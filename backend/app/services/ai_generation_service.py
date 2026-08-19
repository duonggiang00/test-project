"""Governed lifecycle for AI-generated content (AI-002) and advisory AI
grade suggestions (AI-009).

Enforces the approved state machine from `CANONICAL_PROJECT_SPEC.md` §9.2:

    requested -> processing -> generated -> awaiting_review
              -> approved | rejected -> published

Three mechanisms guard every transition, all required by the AI-001-009
change contract:

1. `ALLOWED_TRANSITIONS` -- an explicit allowlist. Anything absent is
   refused, which is what makes `generated -> published` impossible rather
   than merely unimplemented.
2. `version` -- optimistic concurrency. A transition only lands if the row's
   version still matches what the caller read.
3. `SELECT ... FOR UPDATE` -- PostgreSQL row locking, so two concurrent
   reviewers serialize instead of racing.

Authorization reuses the Batch B policy layer (`evaluate_owned_resource`),
and every accepted transition commits exactly one audit event atomically
with the state change, following
`AuthorizationService.commit_with_audit`'s flush-then-single-commit shape.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.permissions import Permission
from app.models.ai_generation import (
    AI_JOB_STATUSES,
    AIGenerationJob,
    AIGradeSuggestion,
)
from app.models.user import User
from app.services.authorization_service import AuthorizationService

# The only legal (from, to) pairs. `generated -> published` is deliberately
# absent: publication must pass through review, per spec §9.2's "No direct
# `generated -> published` transition is allowed."
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("requested", "processing"),
        ("requested", "failed"),
        ("processing", "generated"),
        ("processing", "failed"),
        ("generated", "awaiting_review"),
        ("generated", "failed"),
        ("awaiting_review", "approved"),
        ("awaiting_review", "rejected"),
        ("approved", "published"),
    }
)

# Transitions a human reviewer performs, versus ones the generation pipeline
# performs. Only the former record a reviewer.
_REVIEW_TRANSITIONS: frozenset[str] = frozenset({"approved", "rejected"})

_TRANSITION_AUDIT_ACTIONS: dict[str, str] = {
    "processing": "ai.generation.processing",
    "generated": "ai.generation.generated",
    "awaiting_review": "ai.generation.awaiting_review",
    "approved": "ai.generation.approved",
    "rejected": "ai.generation.rejected",
    "published": "ai.generation.published",
    "failed": "ai.generation.failed",
}


class AIGenerationService:
    @staticmethod
    def create_job(
        db: Session,
        *,
        owner_id: UUID,
        material_id: UUID,
        use_case: str,
    ) -> AIGenerationJob:
        """Create a job in `requested`. Caller owns the transaction."""
        job = AIGenerationJob(
            owner_id=owner_id,
            material_id=material_id,
            use_case=use_case,
            status="requested",
            version=1,
        )
        db.add(job)
        db.flush()
        return job

    @staticmethod
    def get_job_for_review(
        db: Session,
        job_id: UUID,
        current_user: User,
        *,
        lock: bool = False,
    ) -> AIGenerationJob:
        """Fetch a job the actor is allowed to review.

        Cross-owner and missing ids are indistinguishable (canonical 404),
        matching the existence-hiding discipline the rest of the codebase
        applies to owned resources.
        """
        statement = select(AIGenerationJob).where(AIGenerationJob.id == job_id)
        if lock:
            statement = statement.with_for_update()
        job = db.scalar(statement)
        if job is None:
            raise AppException(status_code=404, error_code="AI_JOB_NOT_FOUND")

        decision = AuthorizationService.owned_resource_decision(
            current_user,
            Permission.APPROVE_OWNED_AI_CONTENT,
            job.owner_id,
        )
        if not decision.allowed:
            raise AppException(status_code=404, error_code="AI_JOB_NOT_FOUND")
        return job

    @staticmethod
    def list_jobs_statement(
        current_user: User,
        *,
        status: str | None = None,
        material_id: UUID | None = None,
    ):
        """Owner-scoped review queue, newest first.

        Scoping happens in SQL rather than after the fetch so another
        teacher's jobs never appear in a page count, matching
        `scope_owned_statement`'s treatment of every other owned list.
        """
        if status is not None and status not in AI_JOB_STATUSES:
            raise AppException(status_code=422, error_code="AI_JOB_INVALID_STATUS")
        statement = AuthorizationService.scope_owned_statement(
            select(AIGenerationJob),
            current_user,
            Permission.APPROVE_OWNED_AI_CONTENT,
            AIGenerationJob.owner_id,
        )
        if status is not None:
            statement = statement.where(AIGenerationJob.status == status)
        if material_id is not None:
            statement = statement.where(AIGenerationJob.material_id == material_id)
        return statement.order_by(
            AIGenerationJob.created_at.desc(), AIGenerationJob.id
        )

    @staticmethod
    def assert_transition_allowed(current_status: str, target_status: str) -> None:
        if (current_status, target_status) not in ALLOWED_TRANSITIONS:
            raise AppException(
                status_code=409,
                error_code="AI_JOB_INVALID_TRANSITION",
            )

    @staticmethod
    def transition(
        db: Session,
        job: AIGenerationJob,
        target_status: str,
        *,
        actor: User | None = None,
        expected_version: int | None = None,
        draft_payload: Any | None = None,
        failure_code: str | None = None,
    ) -> AIGenerationJob:
        """Apply one allowlisted transition in place. Caller commits.

        `expected_version` implements optimistic concurrency: when supplied
        and stale, the transition is refused rather than silently clobbering
        a concurrent reviewer's decision.
        """
        AIGenerationService.assert_transition_allowed(job.status, target_status)

        if expected_version is not None and job.version != expected_version:
            raise AppException(
                status_code=409,
                error_code="AI_JOB_VERSION_CONFLICT",
            )

        now = datetime.now(timezone.utc)
        job.status = target_status
        job.version = job.version + 1

        if draft_payload is not None:
            job.draft_payload = draft_payload
        if failure_code is not None:
            job.failure_code = failure_code

        if target_status in _REVIEW_TRANSITIONS:
            if actor is None:
                raise AppException(
                    status_code=409,
                    error_code="AI_JOB_REVIEWER_REQUIRED",
                )
            # Recorded from the acting request, never copied from owner_id:
            # "The reviewer cannot be inferred from the generation actor."
            job.reviewer_id = actor.id
            job.reviewed_at = now
        if target_status == "published":
            job.published_at = now

        db.flush()
        return job

    @staticmethod
    def commit_transition(
        db: Session,
        job: AIGenerationJob,
        target_status: str,
        *,
        actor: User,
        expected_version: int | None = None,
        draft_payload: Any | None = None,
        failure_code: str | None = None,
        override_permission: Permission | None = None,
        override_entity_type: str | None = None,
        override_entity_id: UUID | None = None,
        override_operation: str | None = None,
        request_id: str | None = None,
        audit_metadata: dict[str, Any] | None = None,
    ) -> AIGenerationJob:
        """Transition and commit atomically with exactly one audit event.

        The `override_*` arguments are passed straight through to
        `commit_with_audit`'s conditional `admin.override` layer, so a
        non-owning admin driving a transition still produces the same
        `admin.override` event the rest of the codebase records. They are
        optional because the owning teacher's own transitions need no
        override event, and the background generation worker acts as the
        material's own uploader.

        `audit_metadata` carries the AI-003 `ERROR_AND_AUDIT_CONTRACTS.md`
        §2.4 projection (prompt version, provider/model, token usage,
        estimated cost, latency, context source ids, restricted-payload id,
        reviewer, outcome). It is merged over the always-present `use_case`,
        and `audit_policy`'s per-action allowlist decides what each
        individual transition may actually carry -- a caller cannot widen
        an action's field set by passing extra keys here.
        """
        previous_status = job.status
        AIGenerationService.transition(
            db,
            job,
            target_status,
            actor=actor,
            expected_version=expected_version,
            draft_payload=draft_payload,
            failure_code=failure_code,
        )
        AuthorizationService.commit_with_audit(
            db,
            actor=actor,
            action=_TRANSITION_AUDIT_ACTIONS[target_status],
            entity_type="ai_generation_job",
            entity_id=job.id,
            owner_id=job.owner_id,
            permission=override_permission,
            override_entity_type=override_entity_type,
            override_entity_id=override_entity_id,
            operation=override_operation,
            changes={"status": {"before": previous_status, "after": target_status}},
            metadata={"use_case": job.use_case, **(audit_metadata or {})},
            request_id=request_id,
        )
        return job


class AIGradeSuggestionService:
    """Advisory-only AI grading (AI-009).

    A suggestion never changes awarded points on creation. Only an explicit
    owner/admin approval applies it, and the existing deterministic
    `GradingService` scoring is untouched and is not reclassified as AI
    grading.
    """

    @staticmethod
    def create_suggestion(
        db: Session,
        *,
        submission_answer_id: UUID,
        owner_id: UUID,
        suggested_points: int,
    ) -> AIGradeSuggestion:
        suggestion = AIGradeSuggestion(
            submission_answer_id=submission_answer_id,
            owner_id=owner_id,
            status="awaiting_review",
            version=1,
            suggested_points=suggested_points,
        )
        db.add(suggestion)
        db.flush()
        return suggestion

    @staticmethod
    def get_for_review(
        db: Session,
        suggestion_id: UUID,
        current_user: User,
        *,
        lock: bool = False,
    ) -> AIGradeSuggestion:
        statement = select(AIGradeSuggestion).where(
            AIGradeSuggestion.id == suggestion_id
        )
        if lock:
            statement = statement.with_for_update()
        suggestion = db.scalar(statement)
        if suggestion is None:
            raise AppException(
                status_code=404, error_code="AI_GRADE_SUGGESTION_NOT_FOUND"
            )

        decision = AuthorizationService.owned_resource_decision(
            current_user,
            Permission.APPROVE_OWNED_AI_CONTENT,
            suggestion.owner_id,
        )
        if not decision.allowed:
            raise AppException(
                status_code=404, error_code="AI_GRADE_SUGGESTION_NOT_FOUND"
            )
        return suggestion
