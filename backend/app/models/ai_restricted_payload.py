"""Restricted storage for the exact rendered prompt and raw provider output
(AI-003/AI-004).

The AI-001-009 change contract is explicit: "Rendered prompt/output lives in
a restricted payload record, not the core audit event." `ERROR_AND_AUDIT_
CONTRACTS.md` §2.4 says the same from the audit side -- "Raw prompts and
retrieved content are sensitive payloads. If stored, they must use
restricted storage, redaction, access control, and a separately approved
retention policy" -- and §2.5 forbids "Unredacted sensitive prompts" in
audit fields outright.

So this table is the *only* place a rendered prompt or a raw model response
is persisted. The corresponding `audit_events` row carries the safe §2.4
projection (prompt version, provider/model, token usage, estimated cost,
latency, context source ids, reviewer, outcome) plus this row's id, and
nothing else. `app.core.safe_payload` structurally refuses to serialize the
raw text into an audit payload even if a future caller tries.

Retention follows `CANONICAL_PROJECT_SPEC.md` §6.3: "Restricted raw AI
prompts and retrieved context are retained for 30 days after the generation
job completes, then purged through the governed lifecycle." That boundary is
stored as data (`expires_at`) rather than recomputed from `created_at` at
purge time, so the retention decision that applied to a given row is
auditable and cannot silently change when the constant does.

Access control lives in `app.services.ai_restricted_payload_service`, which
authorizes every read through the parent `AIGenerationJob`'s existing
owner/admin policy (`evaluate_owned_resource`) rather than a second,
divergent rule of its own.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base

# `CANONICAL_PROJECT_SPEC.md` §6.3's approved 30-day restricted-AI-log
# window. Deliberately a separate constant from `db.soft_delete.RESTORE_WINDOW`
# (which also happens to be 30 days): that one is the user-facing soft-delete
# recovery window, this one is a data-minimization retention limit, and the
# two must be free to diverge without one silently changing the other.
RESTRICTED_PAYLOAD_RETENTION = timedelta(days=30)


def restricted_payload_expiry(completed_at: datetime | None = None) -> datetime:
    """The §6.3 purge boundary for a payload completing at `completed_at`."""
    resolved = completed_at or datetime.now(timezone.utc)
    return resolved + RESTRICTED_PAYLOAD_RETENTION


class AIRestrictedPayload(Base):
    """The rendered prompt and raw provider output for one generation job.

    One row per job: the current pipeline makes exactly one provider call
    per `AIGenerationJob`, and the unique index makes that an enforced
    invariant rather than a convention, so a reader never has to guess which
    of several rows an audit event's `restricted_payload_id` meant.

    `raw_output` is nullable on purpose. A job that failed inside the
    provider call has a rendered prompt but no response, and that prompt is
    exactly what an operator needs to diagnose the failure -- the row is
    still written. Note that no *raw provider error* is stored anywhere:
    `AIProviderError.error_code` is already sanitized at the adapter
    boundary (see `app/ai/provider.py`), so the only failure text this
    system retains is a stable code on `AIGenerationJob.failure_code`.

    The `job_id` foreign key is `ON DELETE CASCADE`, unlike the `RESTRICT`
    used elsewhere in `ai_generation.py`. That is deliberate and is the
    conservative direction here: a restricted payload must never outlive the
    job whose context justifies keeping it, so if a job row ever disappears
    its sensitive payload goes with it rather than being stranded past its
    retention basis.
    """

    __tablename__ = "ai_restricted_payloads"
    __table_args__ = (
        Index(
            "uq_ai_restricted_payloads_job_id",
            "job_id",
            unique=True,
        ),
        Index("ix_ai_restricted_payloads_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "ai_generation_jobs.id",
            name="ai_restricted_payloads_job_id_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    rendered_prompt = Column(Text, nullable=False)
    raw_output = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # The §6.3 boundary, materialized at write time. Purge selects on this
    # column; nothing recomputes it.
    expires_at = Column(DateTime(timezone=True), nullable=False)
