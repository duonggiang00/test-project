from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Literal, NoReturn
from uuid import UUID

from pydantic import JsonValue

from app.core.safe_payload import (
    UnsafeStructuredPayloadError,
    validate_safe_mapping,
)


MAX_AUDIT_PAYLOAD_BYTES = 32 * 1024


@dataclass(frozen=True)
class AuditActionPolicy:
    entity_types: frozenset[str]
    success_roles: frozenset[str]
    denied_roles: frozenset[str]
    failure_roles: frozenset[str]
    owner_requirement: Literal["required", "forbidden", "optional"]
    required_success_change_fields: frozenset[str]
    change_fields: frozenset[str]
    metadata_fields: frozenset[str]
    validate_payload: Callable[
        [dict[str, JsonValue], dict[str, JsonValue]], None
    ]


def _reject_invalid_action_payload() -> NoReturn:
    raise UnsafeStructuredPayloadError(
        "Audit payload does not match its action-specific schema"
    )


def _is_change(
    value: JsonValue,
    *,
    allowed_values: tuple[JsonValue, ...],
) -> bool:
    def is_allowed(candidate: JsonValue) -> bool:
        return any(
            type(candidate) is type(allowed) and candidate == allowed
            for allowed in allowed_values
        )

    return (
        isinstance(value, dict)
        and set(value) == {"before", "after"}
        and is_allowed(value["before"])
        and is_allowed(value["after"])
    )


def _is_uuid(value: JsonValue) -> bool:
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _validate_audit_verify(
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    status = changes.get("status")
    if status is not None and not _is_change(
        status,
        allowed_values=("pending", "verified"),
    ):
        _reject_invalid_action_payload()
    test_case = metadata.get("test_case")
    if test_case is not None and test_case != "audit-core":
        _reject_invalid_action_payload()


def _validate_exam_publish(
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    publication = changes.get("is_published")
    if publication is not None and not _is_change(
        publication,
        allowed_values=(None, False, True),
    ):
        _reject_invalid_action_payload()
    source_ids = metadata.get("context_source_ids")
    if source_ids is not None:
        if not isinstance(source_ids, list) or not source_ids:
            _reject_invalid_action_payload()
        if not all(_is_uuid(value) for value in source_ids):
            _reject_invalid_action_payload()


def _validate_user_create(
    changes: dict[str, JsonValue],
    _metadata: dict[str, JsonValue],
) -> None:
    role = changes.get("role")
    if role is not None and not _is_change(
        role,
        allowed_values=(None, "admin", "teacher", "student"),
    ):
        _reject_invalid_action_payload()
    active = changes.get("is_active")
    if active is not None and not _is_change(
        active,
        allowed_values=(None, False, True),
    ):
        _reject_invalid_action_payload()


# DATA-002 extends this registry as each canonical action is instrumented. An
# action cannot begin writing arbitrary payload fields merely because its name
# is syntactically valid.
AUDIT_ACTION_POLICIES = MappingProxyType(
    {
        "audit.verify": AuditActionPolicy(
            entity_types=frozenset({"audit_test"}),
            success_roles=frozenset({"system"}),
            denied_roles=frozenset({"system"}),
            failure_roles=frozenset({"system"}),
            owner_requirement="forbidden",
            required_success_change_fields=frozenset({"status"}),
            change_fields=frozenset({"status"}),
            metadata_fields=frozenset({"test_case"}),
            validate_payload=_validate_audit_verify,
        ),
        "exam.publish": AuditActionPolicy(
            entity_types=frozenset({"exam"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset({"admin", "student", "teacher"}),
            failure_roles=frozenset({"admin", "teacher"}),
            owner_requirement="required",
            required_success_change_fields=frozenset({"is_published"}),
            change_fields=frozenset({"is_published"}),
            metadata_fields=frozenset({"context_source_ids"}),
            validate_payload=_validate_exam_publish,
        ),
        "user.create": AuditActionPolicy(
            entity_types=frozenset({"user"}),
            success_roles=frozenset({"admin", "system", "teacher"}),
            denied_roles=frozenset(
                {"admin", "student", "system", "teacher"}
            ),
            failure_roles=frozenset({"admin", "system", "teacher"}),
            owner_requirement="forbidden",
            required_success_change_fields=frozenset({"role"}),
            change_fields=frozenset({"is_active", "role"}),
            metadata_fields=frozenset(),
            validate_payload=_validate_user_create,
        ),
    }
)


def validate_audit_action_event(
    *,
    action: str,
    actor_role: str,
    entity_type: str,
    entity_id: str,
    owner_id: UUID | None,
    outcome: Literal["success", "denied", "failure"],
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> tuple[dict[str, JsonValue], dict[str, JsonValue]]:
    policy = AUDIT_ACTION_POLICIES.get(action)
    if policy is None:
        raise UnsafeStructuredPayloadError(
            "Audit action has no registered event policy"
        )
    allowed_roles = {
        "success": policy.success_roles,
        "denied": policy.denied_roles,
        "failure": policy.failure_roles,
    }[outcome]
    if actor_role not in allowed_roles:
        _reject_invalid_action_payload()
    if entity_type not in policy.entity_types or not _is_uuid(entity_id):
        _reject_invalid_action_payload()
    if policy.owner_requirement == "required" and owner_id is None:
        _reject_invalid_action_payload()
    if policy.owner_requirement == "forbidden" and owner_id is not None:
        _reject_invalid_action_payload()

    safe_changes = validate_safe_mapping(
        changes,
        allowed_top_level_fields=policy.change_fields,
        max_serialized_bytes=MAX_AUDIT_PAYLOAD_BYTES,
    )
    safe_metadata = validate_safe_mapping(
        metadata,
        allowed_top_level_fields=policy.metadata_fields,
        max_serialized_bytes=MAX_AUDIT_PAYLOAD_BYTES,
    )
    if (
        outcome == "success"
        and not policy.required_success_change_fields.issubset(safe_changes)
    ):
        _reject_invalid_action_payload()
    policy.validate_payload(safe_changes, safe_metadata)
    return safe_changes, safe_metadata
