from __future__ import annotations

from typing import Any
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
