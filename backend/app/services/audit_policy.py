import re
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

# `<prompt-id>-v<n>`, matching §2.4's `"prompt_version": "exam-generation-v3"`
# and produced by `app.ai.prompts.prompt_version_label`. Anchored and narrow
# so the field cannot become a free-text carrier for prompt content.
_PROMPT_VERSION_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}-v[0-9]{1,4}$")
# A plain non-negative decimal, e.g. §2.4's `"estimated_cost": "0.0123"`.
_DECIMAL_STRING_PATTERN = re.compile(r"^[0-9]{1,12}(\.[0-9]{1,12})?$")


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
    """Metadata for both governed purge roots.

    A soft-deleted `study_material` purge is dated by `deleted_at` and may
    report whether a file was quarantined. An `ai_restricted_payload` purge
    is dated by `expires_at` (the §6.3 30-day boundary) and names its parent
    `job_id`, because once the payload row is gone its own entity id refers
    to nothing and the surviving generation job is the only handle left that
    makes the event interpretable.
    """
    for key in ("deleted_at", "expires_at"):
        value = metadata.get(key)
        if value is not None and not isinstance(value, str):
            _reject_invalid_action_payload()
    quarantined = metadata.get("quarantined")
    if quarantined is not None and not isinstance(quarantined, bool):
        _reject_invalid_action_payload()
    job_id = metadata.get("job_id")
    if job_id is not None and not _is_uuid(job_id):
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


_AI_REVIEW_OUTCOMES = frozenset({"approved", "rejected"})

# The exact `ERROR_AND_AUDIT_CONTRACTS.md` §2.4 field names, grouped by the
# point in the lifecycle at which each becomes known. `use_case` predates
# AI-003 and `restricted_payload_id` is the §2.4-mandated "safe reference"
# standing in for the raw prompt/output, which lives in
# `ai_restricted_payloads` and must never appear here.
_AI_BASE_METADATA = frozenset({"use_case"})
_AI_CALL_METADATA = frozenset(
    {"prompt_version", "provider", "model", "context_source_ids"}
)
_AI_USAGE_METADATA = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "estimated_cost",
        "latency_ms",
        "restricted_payload_id",
    }
)
_AI_REVIEW_METADATA = frozenset({"reviewer_id", "review_outcome"})

# A rendered prompt is not merely unlisted here -- it is unrepresentable.
# `safe_payload._is_sensitive_key` rejects `prompt`/`raw_prompt`/
# `prompt_text`/`context`/`document_content` and friends outright, and the
# per-action allowlist below rejects any field it has not been told about,
# so both the key and the allowlist have to be defeated for raw content to
# reach `audit_events`.
_AI_METADATA_BY_ACTION: dict[str, frozenset[str]] = {
    # Requested/processing: the prompt has been rendered and the model
    # resolved, but nothing has come back yet.
    "ai.generation.processing": _AI_BASE_METADATA | _AI_CALL_METADATA,
    # Completion: the full §2.4 usage/cost/latency set.
    "ai.generation.generated": (
        _AI_BASE_METADATA | _AI_CALL_METADATA | _AI_USAGE_METADATA
    ),
    "ai.generation.awaiting_review": _AI_BASE_METADATA,
    "ai.generation.approved": _AI_BASE_METADATA | _AI_REVIEW_METADATA,
    "ai.generation.rejected": _AI_BASE_METADATA | _AI_REVIEW_METADATA,
    "ai.generation.published": _AI_BASE_METADATA | _AI_REVIEW_METADATA,
    # A failure has a prompt and a latency but no usable output, so it gets
    # the call metadata plus the two usage fields that survive a failed call.
    "ai.generation.failed": (
        _AI_BASE_METADATA
        | _AI_CALL_METADATA
        | frozenset({"latency_ms", "restricted_payload_id"})
    ),
}


def _reject_unless_non_negative_int(value: JsonValue) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _reject_invalid_action_payload()


def _validate_ai_call_metadata(
    _changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    """The §2.4 call-identity fields, shared by chat and generation.

    Chat has no job and therefore no status change, so it reuses only this
    half of the checks. Every field is type-checked rather than merely
    allowlisted, so a caller cannot smuggle document text through, say,
    `model` without it also having to pass `safe_payload`'s value scan.
    """
    use_case = metadata.get("use_case")
    if use_case is not None and use_case not in _AI_USE_CASES:
        _reject_invalid_action_payload()

    prompt_version = metadata.get("prompt_version")
    if prompt_version is not None and (
        not isinstance(prompt_version, str)
        or not _PROMPT_VERSION_PATTERN.fullmatch(prompt_version)
    ):
        _reject_invalid_action_payload()

    for key in ("provider", "model"):
        value = metadata.get(key)
        if value is not None and (
            not isinstance(value, str) or not value or len(value) > 128
        ):
            _reject_invalid_action_payload()

    source_ids = metadata.get("context_source_ids")
    if source_ids is not None:
        if not isinstance(source_ids, list) or not source_ids:
            _reject_invalid_action_payload()
        if not all(_is_uuid(value) for value in source_ids):
            _reject_invalid_action_payload()


def _validate_ai_generation_transition(
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    """A `{before, after}` status pair plus the §2.4 AI metadata fields.

    AI-003 widened this from the status-only shape AI-002 shipped. What did
    *not* widen: every field here is a safe projection -- an identifier, a
    version label, a count, or an outcome. The rendered prompt and the raw
    provider output are in `ai_restricted_payloads`, referenced by
    `restricted_payload_id`, exactly as §2.4 requires ("The core audit
    record should prefer prompt version and safe references over duplicating
    raw sensitive content").

    Each field is type-checked rather than merely allowlisted, so a caller
    cannot smuggle a paragraph of document text through, say, `model`
    without it also passing `safe_payload`'s value scan.
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

    prompt_version = metadata.get("prompt_version")
    if prompt_version is not None and (
        not isinstance(prompt_version, str)
        or not _PROMPT_VERSION_PATTERN.fullmatch(prompt_version)
    ):
        _reject_invalid_action_payload()

    for key in ("provider", "model"):
        value = metadata.get(key)
        if value is not None and (
            not isinstance(value, str) or not value or len(value) > 128
        ):
            _reject_invalid_action_payload()

    for key in ("input_tokens", "output_tokens", "latency_ms"):
        value = metadata.get(key)
        if value is not None:
            _reject_unless_non_negative_int(value)

    # Serialized as a decimal string (§2.4 shows `"0.0123"`), or explicitly
    # null when no approved price list covers the model -- see
    # `app/ai/cost_policy.py`. A float is refused so cost never silently
    # picks up binary rounding error on its way into the record.
    if "estimated_cost" in metadata:
        estimated_cost = metadata["estimated_cost"]
        if estimated_cost is not None and (
            not isinstance(estimated_cost, str)
            or not _DECIMAL_STRING_PATTERN.fullmatch(estimated_cost)
        ):
            _reject_invalid_action_payload()

    source_ids = metadata.get("context_source_ids")
    if source_ids is not None:
        if not isinstance(source_ids, list) or not source_ids:
            _reject_invalid_action_payload()
        if not all(_is_uuid(value) for value in source_ids):
            _reject_invalid_action_payload()

    for key in ("reviewer_id", "restricted_payload_id"):
        value = metadata.get(key)
        if value is not None and not _is_uuid(value):
            _reject_invalid_action_payload()

    review_outcome = metadata.get("review_outcome")
    if review_outcome is not None and review_outcome not in _AI_REVIEW_OUTCOMES:
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


def _validate_submission_grade_override(
    changes: dict[str, JsonValue],
    metadata: dict[str, JsonValue],
) -> None:
    """A manual grade correction: numeric before/after pairs and safe ids.

    Note what is *not* here: the teacher's typed reason. `safe_payload`
    rejects any string carrying a control character, an email, or a
    path-shaped token, so a reason with a line break would fail the whole
    write and turn an ordinary correction into a 500. The prose lives on
    `submission_answers.override_reason`; this event keeps only scalars, the
    same split AI-003 uses for rendered prompts.

    `bool` is rejected explicitly everywhere a number is expected because
    `bool` subclasses `int`.
    """
    for field in ("points_awarded", "total_score"):
        change = changes.get(field)
        if change is None:
            continue
        if not isinstance(change, dict) or set(change) != {"before", "after"}:
            _reject_invalid_action_payload()
        for key in ("before", "after"):
            value = change[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                _reject_invalid_action_payload()

    question_id = metadata.get("question_id")
    if question_id is not None and not _is_uuid(question_id):
        _reject_invalid_action_payload()

    max_score = metadata.get("max_score")
    if max_score is not None and (
        isinstance(max_score, bool) or not isinstance(max_score, (int, float))
    ):
        _reject_invalid_action_payload()


_ADMIN_OVERRIDE_OPERATIONS = frozenset(
    {
        # AI-002 review decisions. `publish` already covered writing the
        # approved content out; approving and rejecting a draft are distinct
        # decisions and are named as such rather than folded into `update`.
        "approve",
        "reject",
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
                    # An admin reviewing another teacher's AI draft is an
                    # override like any other and must be auditable as one
                    # (AI-002).
                    "ai_generation_job",
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
        # A teacher/admin correcting a stored grade. Distinct from
        # `submission.graded`, which is the student's own submit and is
        # locked to `success_roles={"student"}`. The two also disagree on
        # `owner_id` by necessity: `submission.graded` names the student,
        # while this action names the exam's creator, because that is the
        # ownership the grading permission is evaluated against (see
        # `HistoryService.override_answer_grade`).
        "submission.grade_override": AuditActionPolicy(
            entity_types=frozenset({"submission"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset({"admin", "teacher"}),
            failure_roles=frozenset({"admin", "teacher"}),
            owner_requirement="required",
            required_success_change_fields=frozenset(
                {"points_awarded", "total_score"}
            ),
            change_fields=frozenset({"points_awarded", "total_score"}),
            metadata_fields=frozenset({"question_id", "max_score"}),
            validate_payload=_validate_submission_grade_override,
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
        # Both purge actions accept exactly the two governed purge roots and
        # no others (AI-004). Widening this to `ai_restricted_payload` is
        # what lets the 30-day restricted-log expiry run through the same
        # audited lifecycle as material purge; it does not make any other
        # entity purgeable, because `purge_service.PURGE_ALLOWLIST` -- not
        # this registry -- decides what can be deleted.
        "purge.requested": AuditActionPolicy(
            entity_types=frozenset({"ai_restricted_payload", "study_material"}),
            success_roles=frozenset({"admin"}),
            denied_roles=frozenset({"admin"}),
            failure_roles=frozenset({"admin"}),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset({"deleted_at", "expires_at", "job_id"}),
            validate_payload=_validate_purge_event,
        ),
        "purge.completed": AuditActionPolicy(
            entity_types=frozenset({"ai_restricted_payload", "study_material"}),
            success_roles=frozenset({"admin"}),
            denied_roles=frozenset({"admin"}),
            failure_roles=frozenset({"admin"}),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=frozenset(
                {"deleted_at", "expires_at", "job_id", "quarantined"}
            ),
            validate_payload=_validate_purge_event,
        ),
        # AI-003 widens each action to exactly the §2.4 metadata it can
        # actually know at that point in the lifecycle -- an approval has a
        # reviewer but no token usage, a completion has token usage but no
        # reviewer -- so an event cannot carry a field it had no way to
        # observe.
        **{
            action: AuditActionPolicy(
                entity_types=frozenset({"ai_generation_job"}),
                success_roles=frozenset({"admin", "teacher"}),
                denied_roles=frozenset({"admin", "teacher"}),
                failure_roles=frozenset({"admin", "teacher"}),
                owner_requirement="required",
                required_success_change_fields=frozenset({"status"}),
                change_fields=frozenset({"status"}),
                metadata_fields=metadata_fields,
                validate_payload=_validate_ai_generation_transition,
            )
            for action, metadata_fields in _AI_METADATA_BY_ACTION.items()
        },
        # A chat turn is a provider call against one authorized material, so
        # the event names the material rather than a generation job -- chat
        # produces no publishable draft and therefore no job. It carries the
        # same §2.4 call-identity fields as `ai.generation.processing`; the
        # completion-side usage/cost fields are absent because the streaming
        # path has no single point at which a complete `GenerateResult` with
        # token accounting exists.
        "ai.chat.requested": AuditActionPolicy(
            entity_types=frozenset({"study_material"}),
            success_roles=frozenset({"admin", "teacher"}),
            denied_roles=frozenset({"admin", "teacher"}),
            failure_roles=frozenset({"admin", "teacher"}),
            owner_requirement="required",
            required_success_change_fields=frozenset(),
            change_fields=frozenset(),
            metadata_fields=_AI_BASE_METADATA | _AI_CALL_METADATA,
            validate_payload=_validate_ai_call_metadata,
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
