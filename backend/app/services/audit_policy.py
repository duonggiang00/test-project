from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Literal, NoReturn
from uuid import UUID

from pydantic import JsonValue

from app.core.safe_payload import (
    UnsafeStructuredPayloadError,
    validate_safe_mapping,
)
from app.core.permissions import Permission


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


_RESTORE_ENTITY_TYPES = frozenset(
    {"exam", "question", "study_material", "topic", "user"}
)


def _validate_restore(
    changes: dict[str, JsonValue],
    _metadata: dict[str, JsonValue],
) -> None:
    deleted_at = changes.get("deleted_at")
    if deleted_at is None:
        return
    if not isinstance(deleted_at, dict) or set(deleted_at) != {"before", "after"}:
        _reject_invalid_action_payload()
    before = deleted_at.get("before")
    after = deleted_at.get("after")
    if not isinstance(before, str) or not before:
        _reject_invalid_action_payload()
    if after is not None:
        _reject_invalid_action_payload()


def _validate_purge_event(
    _changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    deleted_at = metadata.get("deleted_at")
    if deleted_at is not None and not isinstance(deleted_at, str):
        _reject_invalid_action_payload()
    quarantined = metadata.get("quarantined")
    if quarantined is not None and not isinstance(quarantined, bool):
        _reject_invalid_action_payload()


_AI_JOB_STATUSES = frozenset(
    {
        "requested",
        "processing",
        "generated",
        "awaiting_review",
        "approved",
        "rejected",
        "published",
        "failed",
    }
)

_AI_USE_CASES = frozenset(
    {
        "chat",
        "question_generation",
        "flashcard_generation",
        "topic_brief_generation",
    }
)


def _validate_ai_generation_transition(
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    """Only a `{before, after}` status pair drawn from the canonical states.

    The AI-001-009 change contract puts prompt/provider/token/cost/latency
    metadata in AI-003's scope and the rendered prompt itself in a separate
    restricted payload store, so a transition event carries nothing beyond
    its status change and use case.
    """
    status = changes.get("status")
    if not isinstance(status, dict) or set(status) != {"before", "after"}:
        _reject_invalid_action_payload()
    before = status.get("before")
    after = status.get("after")
    if before not in _AI_JOB_STATUSES or after not in _AI_JOB_STATUSES:
        _reject_invalid_action_payload()
    if before == after:
        _reject_invalid_action_payload()

    use_case = metadata.get("use_case")
    if use_case is not None and use_case not in _AI_USE_CASES:
        _reject_invalid_action_payload()


def _validate_no_extra_payload(
    _changes: dict[str, JsonValue],
    _metadata: dict[str, JsonValue],
) -> None:
    # `change_fields`/`metadata_fields` are already empty for these actions,
    # so `validate_safe_mapping`'s allowlist check has already rejected any
    # provided field before this runs -- nothing further to check here.
    return None


def _validate_material_upload(
    _changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    file_type = metadata.get("file_type")
    if file_type is not None and file_type not in {"pdf", "docx", "pptx", "txt"}:
        _reject_invalid_action_payload()


def _validate_material_delete(
    _changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    cascade = metadata.get("cascade")
    if cascade is not None and not isinstance(cascade, bool):
        _reject_invalid_action_payload()


def _validate_submission_graded(
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    total_score = changes.get("total_score")
    if total_score is not None:
        if not isinstance(total_score, dict) or set(total_score) != {
            "before",
            "after",
        }:
            _reject_invalid_action_payload()
        for key in ("before", "after"):
            value = total_score[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                _reject_invalid_action_payload()
    max_score = metadata.get("max_score")
    if max_score is not None and (
        isinstance(max_score, bool) or not isinstance(max_score, (int, float))
    ):
        _reject_invalid_action_payload()


_ADMIN_OVERRIDE_OPERATIONS = frozenset(
    {
        "bulk_assign",
        "create_child",
        "delete",
        "generate",
        "process",
        "publish",
        "update",
    }
)


def _validate_admin_override(
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    if changes:
        _reject_invalid_action_payload()
    permission = metadata.get("permission")
    operation = metadata.get("operation")
    if permission not in {value.value for value in Permission}:
        _reject_invalid_action_payload()
    if operation not in _ADMIN_OVERRIDE_OPERATIONS:
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
        "admin.override": AuditActionPolicy(
            entity_types=frozenset(
                {
                    "exam",
                    "flashcard",
                    "flashcard_deck",
                    "question",
                    "study_material",
                    "topic",
                    "topic_brief",
                }
            ),
            success_roles=frozenset({"admin"}),
            denied_roles=frozenset({"admin"}),
            failure_roles=frozenset({"admin"}),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset({"operation", "permission"}),
            validate_payload=_validate_admin_override,
        ),
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
        "exam.unpublish": AuditActionPolicy(
            entity_types=frozenset({"exam"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset({"admin", "student", "teacher"}),
            failure_roles=frozenset({"admin", "teacher"}),
            owner_requirement="required",
            required_success_change_fields=frozenset({"is_published"}),
            change_fields=frozenset({"is_published"}),
            metadata_fields=frozenset(),
            validate_payload=_validate_exam_publish,
        ),
        "exam.create": AuditActionPolicy(
            entity_types=frozenset({"exam"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "exam.update": AuditActionPolicy(
            entity_types=frozenset({"exam"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "exam.delete": AuditActionPolicy(
            entity_types=frozenset({"exam"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "topic.create": AuditActionPolicy(
            entity_types=frozenset({"topic"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "topic.update": AuditActionPolicy(
            entity_types=frozenset({"topic"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "topic.delete": AuditActionPolicy(
            entity_types=frozenset({"topic"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "question.create": AuditActionPolicy(
            entity_types=frozenset({"question"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "question.update": AuditActionPolicy(
            entity_types=frozenset({"question"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "question.delete": AuditActionPolicy(
            entity_types=frozenset({"question"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "material.upload": AuditActionPolicy(
            entity_types=frozenset({"study_material"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset({"file_type"}),
            validate_payload=_validate_material_upload,
        ),
        "material.delete": AuditActionPolicy(
            entity_types=frozenset({"study_material"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset({"cascade"}),
            validate_payload=_validate_material_delete,
        ),
        "flashcard_deck.create": AuditActionPolicy(
            entity_types=frozenset({"flashcard_deck"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "flashcard.create": AuditActionPolicy(
            entity_types=frozenset({"flashcard"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="optional",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "submission.graded": AuditActionPolicy(
            entity_types=frozenset({"submission"}),
            success_roles=frozenset({"student"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="required",
            required_success_change_fields=frozenset({"total_score"}),
            change_fields=frozenset({"total_score"}),
            metadata_fields=frozenset({"max_score"}),
            validate_payload=_validate_submission_graded,
        ),
        "user.role_change": AuditActionPolicy(
            entity_types=frozenset({"user"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="forbidden",
            required_success_change_fields=frozenset({"role"}),
            change_fields=frozenset({"role"}),
            metadata_fields=frozenset(),
            validate_payload=_validate_user_create,
        ),
        "user.disable": AuditActionPolicy(
            entity_types=frozenset({"user"}),
            success_roles=frozenset({"admin"}),
            denied_roles=frozenset(),
            failure_roles=frozenset(),
            owner_requirement="forbidden",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(),
            validate_payload=_validate_no_extra_payload,
        ),
        "restore.performed": AuditActionPolicy(
            entity_types=_RESTORE_ENTITY_TYPES,
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset({"admin", "teacher"}),
            failure_roles=frozenset({"admin", "teacher"}),
            owner_requirement="optional",
            required_success_change_fields=frozenset({"deleted_at"}),
            change_fields=frozenset({"deleted_at"}),
            metadata_fields=frozenset(),
            validate_payload=_validate_restore,
        ),
        "purge.requested": AuditActionPolicy(
            entity_types=frozenset({"study_material"}),
            success_roles=frozenset({"admin"}),
            denied_roles=frozenset({"admin"}),
            failure_roles=frozenset({"admin"}),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset({"deleted_at"}),
            validate_payload=_validate_purge_event,
        ),
        "purge.completed": AuditActionPolicy(
            entity_types=frozenset({"study_material"}),
            success_roles=frozenset({"admin"}),
            denied_roles=frozenset({"admin"}),
            failure_roles=frozenset({"admin"}),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset({"deleted_at", "quarantined"}),
            validate_payload=_validate_purge_event,
        ),
        **{
            action: AuditActionPolicy(
                entity_types=frozenset({"ai_generation_job"}),
                success_roles=frozenset({"admin", "teacher"}),
                denied_roles=frozenset({"admin", "teacher"}),
                failure_roles=frozenset({"admin", "teacher"}),
                owner_requirement="required",
                required_success_change_fields=frozenset({"status"}),
                change_fields=frozenset({"status"}),
                metadata_fields=frozenset({"use_case"}),
                validate_payload=_validate_ai_generation_transition,
            )
            for action in (
                "ai.generation.processing",
                "ai.generation.generated",
                "ai.generation.awaiting_review",
                "ai.generation.approved",
                "ai.generation.rejected",
                "ai.generation.published",
                "ai.generation.failed",
            )
        },
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
