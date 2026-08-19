"""Write and access-controlled read of restricted AI payloads (AI-004).

`ai_restricted_payloads` holds the only copy of a rendered prompt or raw
model response this system keeps, so reading it is a sensitive operation and
gets the same treatment as reading the generation job it belongs to.

The access rule is deliberately *derived*, not restated: every read
authorizes through `AIGenerationService.get_job_for_review`, which runs
`AuthorizationService.owned_resource_decision` ->
`app.core.permissions.evaluate_owned_resource` against
`Permission.APPROVE_OWNED_AI_CONTENT`. That yields exactly the required
audience -- admin (via admin override), or the owning teacher, who is also
the only non-admin who can ever be recorded as `reviewer_id`, since
`get_job_for_review` is likewise the gate on approve/reject. Writing a
second, parallel ownership rule here would be a place for the two to drift
apart; there is only one rule and this module borrows it.

Cross-owner reads therefore fail the same way a cross-owner job read fails:
`AI_JOB_NOT_FOUND` with status 404, never 403, so probing an id cannot
distinguish "someone else's payload" from "no such payload".
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.ai_generation import AIGenerationJob
from app.models.ai_restricted_payload import (
    AIRestrictedPayload,
    restricted_payload_expiry,
)
from app.models.user import User
from app.services.ai_generation_service import AIGenerationService


class AIRestrictedPayloadService:
    @staticmethod
    def store(
        db: Session,
        *,
        job: AIGenerationJob,
        rendered_prompt: str,
        raw_output: str | None,
        completed_at: datetime | None = None,
    ) -> AIRestrictedPayload:
        """Persist one job's prompt/output. Caller owns the transaction.

        Flushed but not committed: the caller
        (`MaterialService._run_generation_job`) hands the resulting id to the
        `ai.generation.generated`/`failed` audit event and commits both
        together, so an audit row can never reference a payload row that
        does not exist, nor a payload row exist with no audited reason for
        its retention clock to have started.

        `expires_at` is stamped here, at the moment the provider call
        resolves -- that is what `CANONICAL_PROJECT_SPEC.md` §6.3's "30 days
        after the generation job completes" means for a payload: the
        generation work is over, and the later review/publication decisions
        do not extend the raw prompt's life.
        """
        resolved_completed_at = completed_at or datetime.now(timezone.utc)
        payload = AIRestrictedPayload(
            job_id=job.id,
            rendered_prompt=rendered_prompt,
            raw_output=raw_output,
            expires_at=restricted_payload_expiry(resolved_completed_at),
        )
        db.add(payload)
        db.flush()
        return payload

    @staticmethod
    def get_for_job(
        db: Session,
        job_id: UUID,
        current_user: User,
    ) -> AIRestrictedPayload:
        """Read one job's restricted payload, or raise a canonical 404.

        Authorization happens *before* the payload is loaded, against the
        parent job, so an unauthorized caller never causes sensitive text to
        be read out of the database at all -- not even into memory to be
        discarded afterwards.
        """
        AIGenerationService.get_job_for_review(db, job_id, current_user)
        payload = db.scalar(
            select(AIRestrictedPayload).where(AIRestrictedPayload.job_id == job_id)
        )
        if payload is None:
            # Expired-and-purged (§6.3) and never-written are the same
            # answer to a reader: there is nothing to show.
            raise AppException(
                status_code=404, error_code="AI_RESTRICTED_PAYLOAD_NOT_FOUND"
            )
        return payload
