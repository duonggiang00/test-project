"""Durable receipt for the two-phase file purge in `purge_service.py`.

Per the DATA-001-006-009 change contract, "interruption leaves a recoverable
job/receipt for deterministic retry rather than a missing active file or
false success." `_attempt_purge_one` quarantines a material's file, then
hard-deletes its `StudyMaterial` row and commits, then calls
`storage.finalize_purge()` *outside* that transaction. If the process dies
in the narrow window between the commit and `finalize_purge()` actually
running, the row is correctly gone but the file is stuck in quarantine with
no `StudyMaterial` row left for a future `plan_purge`/`apply_purge` scan to
ever find again -- a permanent disk-space leak. This ledger closes that gap.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base

PURGE_JOB_STATUSES = ("pending_finalize", "completed")


class PurgeJob(Base):
    """One row per in-flight or completed quarantine-finalize step.

    Written with `status="pending_finalize"` in the SAME transaction that
    quarantines the file and hard-deletes the owning `StudyMaterial` row, so
    if that transaction rolls back, this row never existed either --
    consistent with the quarantine restore. `material_id` is intentionally
    NOT a foreign key: by the time this row is durable, the `StudyMaterial`
    row it names is already gone (that is the entire point -- a receipt
    that outlives the row it was about). After `finalize_purge()` succeeds,
    the row is updated to `status="completed"` in its own follow-up
    transaction; `audit_events` remains the append-only source of truth for
    the completed purge, so this ledger is purely an operational recovery
    aid, not an audit record.

    `reconcile_pending_purge_jobs` (see `purge_service.py`) scans for
    `pending_finalize` rows and re-runs `finalize_purge()` for each --
    idempotent because `LocalFileStorage.finalize_purge` unlinks with
    `missing_ok=True`, so re-finalizing an already-removed file is a safe
    no-op.
    """

    __tablename__ = "purge_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_finalize', 'completed')",
            name="ck_purge_jobs_status",
        ),
        Index("ix_purge_jobs_status", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    quarantine_token = Column(String(1024), nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default="pending_finalize",
        server_default="pending_finalize",
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
