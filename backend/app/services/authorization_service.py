from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.core.correlation import get_current_request_id, new_correlation_id
from app.core.exceptions import AppException
from app.core.permissions import (
    Actor,
    Permission,
    PolicyDecision,
    evaluate_owned_resource,
    require_owner_scope,
)
from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.services.audit_service import AuditService


class AuthorizationService:
    @staticmethod
    def scope_owned_statement(
        statement: Select[Any],
        actor: Actor,
        permission: Permission,
        owner_column: Any,
    ) -> Select[Any]:
        decision = require_owner_scope(actor, permission)
        if decision.scoped_owner_id is not None:
            return statement.where(owner_column == decision.scoped_owner_id)
        return statement

    @staticmethod
    def owned_resource_decision(
        actor: Actor,
        permission: Permission,
        owner_id: UUID | None,
    ) -> PolicyDecision:
        return evaluate_owned_resource(actor, permission, owner_id)

    @staticmethod
    def record_admin_override_if_required(
        db: Session,
        *,
        actor: Actor,
        permission: Permission,
        entity_type: str,
        entity_id: UUID,
        owner_id: UUID | None,
        operation: str,
        request_id: str | None = None,
    ) -> None:
        decision = evaluate_owned_resource(actor, permission, owner_id)
        if not decision.allowed:
            raise AppException(
                status_code=403,
                error_code="NOT_ENOUGH_PERMISSIONS",
            )
        if not decision.audit_required:
            return
        AuditService.record(
            db,
            AuditEventCreate(
                request_id=(
                    request_id
                    or get_current_request_id()
                    or new_correlation_id()
                ),
                actor=AuditActor(
                    actor_type="user",
                    user_id=actor.id,
                    role="admin",
                ),
                action="admin.override",
                entity=AuditEntity(
                    type=entity_type,
                    id=str(entity_id),
                    owner_id=owner_id,
                ),
                outcome="success",
                changes={},
                metadata={
                    "permission": permission.value,
                    "operation": operation,
                },
            ),
        )

    @staticmethod
    def commit_with_admin_override(
        db: Session,
        *,
        actor: Actor,
        permission: Permission,
        entity_type: str,
        entity_id: UUID,
        owner_id: UUID | None,
        operation: str,
        request_id: str | None = None,
    ) -> None:
        try:
            AuthorizationService.record_admin_override_if_required(
                db,
                actor=actor,
                permission=permission,
                entity_type=entity_type,
                entity_id=entity_id,
                owner_id=owner_id,
                operation=operation,
                request_id=request_id,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def commit_with_audit(
        db: Session,
        *,
        actor: Actor,
        action: str,
        entity_type: str,
        entity_id: UUID,
        owner_id: UUID | None,
        permission: Permission | None = None,
        override_entity_type: str | None = None,
        override_entity_id: UUID | None = None,
        operation: str | None = None,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        """Authorize, record one action-specific success event, and commit.

        DATA-002 counterpart to `commit_with_admin_override`/`commit_restore`:
        unlike `commit_with_admin_override`'s conditional `admin.override`
        event, the `action` event here is always recorded on success,
        regardless of actor. When `permission` is given, this additionally
        layers the existing conditional `admin.override` check/event (using
        `override_entity_type`/`override_entity_id` when the audited action
        targets a child entity of the resource the permission check scopes
        against, e.g. a question created under an exam) before the
        action-specific event, mirroring `commit_with_admin_override`'s
        authorize-then-commit shape. `permission=None` skips the
        admin-override layer entirely -- appropriate for creates, which are
        always self-owned and have no owned-permission scope to check.
        """
        try:
            if permission is not None:
                AuthorizationService.record_admin_override_if_required(
                    db,
                    actor=actor,
                    permission=permission,
                    entity_type=override_entity_type or entity_type,
                    entity_id=override_entity_id or entity_id,
                    owner_id=owner_id,
                    operation=operation or "update",
                    request_id=request_id,
                )
            resolved_request_id = (
                request_id or get_current_request_id() or new_correlation_id()
            )
            AuditService.record(
                db,
                AuditEventCreate(
                    request_id=resolved_request_id,
                    actor=AuditActor(
                        actor_type="user",
                        user_id=actor.id,
                        role=cast(
                            Literal["admin", "teacher", "student", "system"],
                            actor.role,
                        ),
                    ),
                    action=action,
                    entity=AuditEntity(
                        type=entity_type,
                        id=str(entity_id),
                        owner_id=owner_id,
                    ),
                    outcome="success",
                    changes=changes or {},
                    metadata=metadata or {},
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def commit_restore(
        db: Session,
        *,
        actor: Actor,
        permission: Permission,
        entity_type: str,
        entity_id: UUID,
        owner_id: UUID | None,
        deleted_at_before: datetime,
        request_id: str | None = None,
    ) -> None:
        """Authorize and audit a soft-delete restore, then commit.

        Mirrors `commit_with_admin_override`'s flush-then-commit shape, but
        always records one `restore.performed` success event -- restore is
        audited for both the owning teacher and an admin override, not just
        for a non-self admin override.
        """
        try:
            decision = evaluate_owned_resource(actor, permission, owner_id)
            if not decision.allowed:
                raise AppException(
                    status_code=403,
                    error_code="NOT_ENOUGH_PERMISSIONS",
                )
            AuditService.record(
                db,
                AuditEventCreate(
                    request_id=(
                        request_id
                        or get_current_request_id()
                        or new_correlation_id()
                    ),
                    actor=AuditActor(
                        actor_type="user",
                        user_id=actor.id,
                        role=cast(
                            Literal["admin", "teacher", "student", "system"],
                            actor.role,
                        ),
                    ),
                    action="restore.performed",
                    entity=AuditEntity(
                        type=entity_type,
                        id=str(entity_id),
                        owner_id=owner_id,
                    ),
                    outcome="success",
                    changes={
                        "deleted_at": {
                            "before": deleted_at_before.isoformat(),
                            "after": None,
                        },
                    },
                    metadata={},
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
