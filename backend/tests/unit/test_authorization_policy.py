import uuid
from dataclasses import dataclass

import pytest

from app.core.exceptions import AppException
from app.core.permissions import (
    Permission,
    PolicyDecisionMode,
    evaluate_owned_resource,
    evaluate_owner_scope,
    evaluate_permission,
    require_permission,
    require_student_self_service,
)
from app.services.authorization_service import AuthorizationService


@dataclass(frozen=True)
class PolicyActor:
    id: uuid.UUID
    role: str


@pytest.mark.unit
@pytest.mark.parametrize(
    ("role", "permission", "allowed", "mode"),
    [
        ("admin", Permission.PURGE_DELETED_DATA, True, PolicyDecisionMode.DIRECT),
        ("teacher", Permission.MANAGE_USERS, True, PolicyDecisionMode.COMPATIBILITY),
        ("teacher", Permission.CREATE_CONTENT, True, PolicyDecisionMode.DIRECT),
        ("teacher", Permission.PURGE_DELETED_DATA, False, PolicyDecisionMode.DENY),
        ("student", Permission.READ_ASSIGNED_CONTENT, True, PolicyDecisionMode.DIRECT),
        ("student", Permission.CREATE_CONTENT, False, PolicyDecisionMode.DENY),
        ("unknown", Permission.READ_ASSIGNED_CONTENT, False, PolicyDecisionMode.DENY),
    ],
)
def test_named_permission_matrix(role, permission, allowed, mode):
    decision = evaluate_permission(role, permission)

    assert decision.allowed is allowed
    assert decision.mode is mode


@pytest.mark.unit
def test_teacher_owner_scope_is_actor_id():
    actor = PolicyActor(uuid.uuid4(), "teacher")

    decision = evaluate_owner_scope(actor, Permission.READ_OWNED_CONTENT)

    assert decision.allowed
    assert decision.mode is PolicyDecisionMode.OWNER
    assert decision.scoped_owner_id == actor.id
    assert not decision.audit_required


@pytest.mark.unit
def test_admin_owner_scope_is_explicit_override():
    actor = PolicyActor(uuid.uuid4(), "admin")

    decision = evaluate_owner_scope(actor, Permission.UPDATE_OWNED_CONTENT)

    assert decision.allowed
    assert decision.mode is PolicyDecisionMode.ADMIN_OVERRIDE
    assert decision.scoped_owner_id is None
    assert decision.audit_required


@pytest.mark.unit
def test_owned_resource_decision_denies_cross_owner_and_legacy_null_to_teacher():
    actor = PolicyActor(uuid.uuid4(), "teacher")

    assert evaluate_owned_resource(
        actor, Permission.READ_OWNED_CONTENT, actor.id
    ).allowed
    assert not evaluate_owned_resource(
        actor, Permission.READ_OWNED_CONTENT, uuid.uuid4()
    ).allowed
    assert not evaluate_owned_resource(
        actor, Permission.READ_OWNED_CONTENT, None
    ).allowed


@pytest.mark.unit
def test_admin_override_audit_is_required_only_for_non_self_owner():
    actor = PolicyActor(uuid.uuid4(), "admin")

    own = evaluate_owned_resource(
        actor, Permission.UPDATE_OWNED_CONTENT, actor.id
    )
    foreign = evaluate_owned_resource(
        actor, Permission.UPDATE_OWNED_CONTENT, uuid.uuid4()
    )
    legacy = evaluate_owned_resource(
        actor, Permission.UPDATE_OWNED_CONTENT, None
    )

    assert not own.audit_required
    assert foreign.audit_required
    assert legacy.audit_required


@pytest.mark.unit
def test_require_permission_uses_canonical_role_denial():
    actor = PolicyActor(uuid.uuid4(), "student")

    with pytest.raises(AppException) as caught:
        require_permission(actor, Permission.CREATE_CONTENT)

    assert caught.value.status_code == 403
    assert caught.value.error_code == "NOT_ENOUGH_PERMISSIONS"


@pytest.mark.unit
def test_student_self_service_rejects_admin_even_if_admin_has_named_permission():
    actor = PolicyActor(uuid.uuid4(), "admin")

    with pytest.raises(AppException) as caught:
        require_student_self_service(actor, Permission.CREATE_SUBMISSION)

    assert caught.value.status_code == 403
    assert caught.value.error_code == "NOT_ENOUGH_PERMISSIONS"


@pytest.mark.unit
def test_admin_override_transaction_helper_rejects_denied_actor():
    actor = PolicyActor(uuid.uuid4(), "teacher")

    with pytest.raises(AppException) as caught:
        AuthorizationService.record_admin_override_if_required(
            object(),
            actor=actor,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="topic",
            entity_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            operation="update",
        )

    assert caught.value.status_code == 403
    assert caught.value.error_code == "NOT_ENOUGH_PERMISSIONS"
