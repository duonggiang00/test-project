from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from fastapi import status

from app.core.exceptions import AppException


class Actor(Protocol):
    id: UUID
    role: str


class Role(StrEnum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class Permission(StrEnum):
    MANAGE_USERS = "manage_users"
    MANAGE_SYSTEM_DATA = "manage_system_data"
    CREATE_CONTENT = "create_content"
    READ_OWNED_CONTENT = "read_owned_content"
    UPDATE_OWNED_CONTENT = "update_owned_content"
    DELETE_OWNED_CONTENT = "delete_owned_content"
    RESTORE_OWNED_CONTENT = "restore_owned_content"
    PUBLISH_OWNED_CONTENT = "publish_owned_content"
    READ_ASSIGNED_CONTENT = "read_assigned_content"
    CREATE_SUBMISSION = "create_submission"
    READ_OWN_SUBMISSION = "read_own_submission"
    READ_OWNED_EXAM_SUBMISSIONS = "read_owned_exam_submissions"
    GRADE_OWNED_EXAM_SUBMISSION = "grade_owned_exam_submission"
    APPROVE_OWNED_AI_CONTENT = "approve_owned_ai_content"
    VIEW_AUDIT_LOG = "view_audit_log"
    ADMIN_OVERRIDE = "admin_override"
    PURGE_DELETED_DATA = "purge_deleted_data"


class PolicyDecisionMode(StrEnum):
    DIRECT = "direct"
    COMPATIBILITY = "compatibility"
    OWNER = "owner"
    ADMIN_OVERRIDE = "admin_override"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    mode: PolicyDecisionMode
    permission: Permission
    scoped_owner_id: UUID | None = None
    audit_required: bool = False


_OWNED_PERMISSIONS = frozenset(
    {
        Permission.READ_OWNED_CONTENT,
        Permission.UPDATE_OWNED_CONTENT,
        Permission.DELETE_OWNED_CONTENT,
        Permission.RESTORE_OWNED_CONTENT,
        Permission.PUBLISH_OWNED_CONTENT,
        Permission.READ_OWNED_EXAM_SUBMISSIONS,
        Permission.GRADE_OWNED_EXAM_SUBMISSION,
        Permission.APPROVE_OWNED_AI_CONTENT,
        Permission.VIEW_AUDIT_LOG,
    }
)

_ROLE_PERMISSIONS = MappingProxyType(
    {
        Role.ADMIN: frozenset(Permission),
        Role.TEACHER: frozenset(
            {
                Permission.MANAGE_USERS,
                Permission.MANAGE_SYSTEM_DATA,
                Permission.CREATE_CONTENT,
                *_OWNED_PERMISSIONS,
            }
        ),
        Role.STUDENT: frozenset(
            {
                Permission.READ_ASSIGNED_CONTENT,
                Permission.CREATE_SUBMISSION,
                Permission.READ_OWN_SUBMISSION,
            }
        ),
    }
)

_COMPATIBILITY_PERMISSIONS = frozenset(
    {Permission.MANAGE_USERS, Permission.MANAGE_SYSTEM_DATA}
)


def parse_role(role: str) -> Role | None:
    try:
        return Role(role)
    except ValueError:
        return None


def evaluate_permission(role: str, permission: Permission) -> PolicyDecision:
    typed_role = parse_role(role)
    if typed_role is None or permission not in _ROLE_PERMISSIONS[typed_role]:
        return PolicyDecision(False, PolicyDecisionMode.DENY, permission)
    if (
        typed_role is Role.TEACHER
        and permission in _COMPATIBILITY_PERMISSIONS
    ):
        return PolicyDecision(
            True,
            PolicyDecisionMode.COMPATIBILITY,
            permission,
        )
    return PolicyDecision(True, PolicyDecisionMode.DIRECT, permission)


def require_permission(actor: Actor, permission: Permission) -> PolicyDecision:
    decision = evaluate_permission(actor.role, permission)
    if not decision.allowed:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="NOT_ENOUGH_PERMISSIONS",
        )
    return decision


def evaluate_owner_scope(actor: Actor, permission: Permission) -> PolicyDecision:
    if permission not in _OWNED_PERMISSIONS:
        raise ValueError(f"{permission.value} is not an owner-scoped permission")
    base = evaluate_permission(actor.role, permission)
    if not base.allowed:
        return base
    typed_role = parse_role(actor.role)
    if typed_role is Role.ADMIN:
        return PolicyDecision(
            True,
            PolicyDecisionMode.ADMIN_OVERRIDE,
            permission,
            scoped_owner_id=None,
            audit_required=True,
        )
    if typed_role is Role.TEACHER:
        return PolicyDecision(
            True,
            PolicyDecisionMode.OWNER,
            permission,
            scoped_owner_id=actor.id,
        )
    return PolicyDecision(False, PolicyDecisionMode.DENY, permission)


def require_owner_scope(actor: Actor, permission: Permission) -> PolicyDecision:
    decision = evaluate_owner_scope(actor, permission)
    if not decision.allowed:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="NOT_ENOUGH_PERMISSIONS",
        )
    return decision


def evaluate_owned_resource(
    actor: Actor,
    permission: Permission,
    owner_id: UUID | None,
) -> PolicyDecision:
    scope = evaluate_owner_scope(actor, permission)
    if not scope.allowed:
        return scope
    if scope.mode is PolicyDecisionMode.ADMIN_OVERRIDE:
        return PolicyDecision(
            True,
            PolicyDecisionMode.ADMIN_OVERRIDE,
            permission,
            audit_required=owner_id != actor.id,
        )
    if owner_id is not None and owner_id == scope.scoped_owner_id:
        return PolicyDecision(
            True,
            PolicyDecisionMode.OWNER,
            permission,
            scoped_owner_id=owner_id,
        )
    return PolicyDecision(False, PolicyDecisionMode.DENY, permission)


def require_student_self_service(actor: Actor, permission: Permission) -> None:
    require_permission(actor, permission)
    if parse_role(actor.role) is not Role.STUDENT:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="NOT_ENOUGH_PERMISSIONS",
        )


def is_admin(actor: Actor) -> bool:
    return parse_role(actor.role) is Role.ADMIN
