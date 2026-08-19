"""Allowlisted, dry-run-capable permanent purge for soft-deleted data (DATA-005).

Per the approved MVP retention policy (`docs/spec/CANONICAL_PROJECT_SPEC.md`
6.3) and the DATA-001-006-009 change contract, permanent purge is
allowlisted, not generic: only `StudyMaterial` rows are eligible. `User`,
`Exam`, `Question`, and `Topic` purge stay blocked in this phase because
their current foreign keys can reach submissions, answers/grades, or
flashcard progress -- protected educational records that are retained
indefinitely in the MVP. `audit_events` is never purged by any code path
here (its table is append-only at the database level besides).

A material is eligible once `deleted_at <= now - RESTORE_WINDOW` (the exact
complementary boundary to `is_restorable`). Even then, `material_service.py`'s
`delete_material` has a `keep_assets` path (and, more subtly, its `cascade`
path) that can leave a material soft-deleted while a `Question`,
`FlashcardDeck`, or `TopicBrief` row still carries its `material_id` --
those foreign keys are `ON DELETE SET NULL`, not `CASCADE`, so a hard delete
would silently null a reference out from under a still-live, or still
soft-deleted-but-retained, educational record. `_material_has_retained_links`
re-checks this immediately before every purge; a surviving reference blocks
purge for that material rather than silently mutating it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session

from app.core.correlation import get_current_request_id, new_correlation_id
from app.core.file_storage import FileStorage, material_file_storage
from app.core.permissions import Actor, Permission, require_permission
from app.db.soft_delete import RESTORE_WINDOW
from app.models.ai_generation import AIGenerationJob
from app.models.ai_restricted_payload import AIRestrictedPayload
from app.models.exam import Question
from app.models.flashcard import FlashcardDeck
from app.models.material import StudyMaterial
from app.models.purge_job import PurgeJob
from app.models.topic_brief import TopicBrief
from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.services.audit_service import AuditService

DEFAULT_PURGE_BATCH_LIMIT = 500


@dataclass(frozen=True)
class PurgeReport:
    action: Literal["plan", "apply"]
    entity: str = "study_material"
    eligible_ids: tuple[UUID, ...] = ()
    purged_ids: tuple[UUID, ...] = ()
    blocked_ids: tuple[UUID, ...] = ()

    @property
    def eligible_count(self) -> int:
        return len(self.eligible_ids)

    @property
    def purged_count(self) -> int:
        return len(self.purged_ids)

    @property
    def blocked_count(self) -> int:
        return len(self.blocked_ids)


@dataclass(frozen=True)
class ReconcileReport:
    action: Literal["reconcile"] = "reconcile"
    entity: str = "purge_job"
    reconciled_material_ids: tuple[UUID, ...] = ()

    @property
    def reconciled_count(self) -> int:
        return len(self.reconciled_material_ids)


def _purge_cutoff() -> datetime:
    return datetime.now(timezone.utc) - RESTORE_WINDOW


def _eligible_material_rows(
    db: Session, *, limit: int | None
) -> list[StudyMaterial]:
    statement = (
        select(StudyMaterial)
        .where(
            StudyMaterial.deleted_at.is_not(None),
            StudyMaterial.deleted_at <= _purge_cutoff(),
        )
        .order_by(StudyMaterial.deleted_at, StudyMaterial.id)
        .execution_options(include_deleted=True)
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).all())


def _material_has_retained_links(db: Session, material_id: UUID) -> bool:
    """True if any row -- live or soft-deleted -- still references this material.

    Includes soft-deleted `Question` rows on purpose: `delete_material`'s
    cascade path soft-deletes linked questions rather than hard-deleting
    them, so they can still carry `material_id` long after both they and the
    material itself are past their own 30-day windows. Questions are never
    purge-eligible, so that reference must keep blocking material purge
    rather than being silently severed.
    """
    return bool(
        db.scalar(
            select(
                exists(
                    select(Question.id).where(
                        Question.material_id == material_id
                    )
                )
                | exists(
                    select(FlashcardDeck.id).where(
                        FlashcardDeck.material_id == material_id
                    )
                )
                | exists(
                    select(TopicBrief.id).where(
                        TopicBrief.material_id == material_id
                    )
                )
            ).execution_options(include_deleted=True)
        )
    )


def plan_purge(
    db: Session, *, batch_limit: int | None = None
) -> PurgeReport:
    """Dry run: preview what `apply_purge` would do without changing anything.

    Every query here is a plain SELECT -- no row is mutated, no file is
    touched, and no audit event is written.
    """
    eligible: list[UUID] = []
    blocked: list[UUID] = []
    for material in _eligible_material_rows(db, limit=batch_limit):
        if _material_has_retained_links(db, material.id):
            blocked.append(material.id)
        else:
            eligible.append(material.id)
    return PurgeReport(
        action="plan",
        eligible_ids=tuple(eligible),
        blocked_ids=tuple(blocked),
    )


def _audit_actor(actor: Actor) -> AuditActor:
    return AuditActor(
        actor_type="user",
        user_id=actor.id,
        role=cast(Literal["admin", "teacher", "student", "system"], actor.role),
    )


def _mark_purge_job_completed(db: Session, purge_job_id: UUID) -> None:
    """Mark a ledger row completed, in its own small follow-up transaction.

    Only called after `storage.finalize_purge()` has already succeeded.
    `audit_events` remains the append-only source of truth for the
    completed purge; this ledger update is purely an operational recovery
    aid, so it is fine for it to land in a separate transaction from the
    quarantine+hard-delete commit above -- if the process dies before this
    runs, `reconcile_pending_purge_jobs` finds the row still
    `pending_finalize` and finishes the job.
    """
    db.execute(
        update(PurgeJob)
        .where(PurgeJob.id == purge_job_id)
        .values(status="completed", completed_at=datetime.now(timezone.utc))
    )
    db.commit()


def _attempt_purge_one(
    db: Session,
    actor: Actor,
    storage: FileStorage,
    material_id: UUID,
    cutoff: datetime,
    resolved_request_id: str,
) -> Literal["purged", "blocked", "skipped"]:
    """Purge exactly one material, or explain why it was left alone.

    Re-fetches and locks the row immediately before acting (so a concurrent
    restore or purge run can never race with this one), re-verifies the
    30-day boundary and the retained-links check, then performs the
    quarantine-audit-delete-audit-ledger-commit sequence as a single
    transaction. On any failure before commit, the transaction rolls back
    and the file (if quarantined) is moved back to its original active path
    before the exception propagates to the caller.

    A `PurgeJob` ledger row (status="pending_finalize") is written in that
    same transaction whenever a file was quarantined, so a crash between
    this commit and the `finalize_purge()` call below leaves a durable,
    recoverable receipt naming exactly which quarantined file still needs
    to be removed -- see `reconcile_pending_purge_jobs` and
    `app/models/purge_job.py`.
    """
    material = db.scalar(
        select(StudyMaterial)
        .where(StudyMaterial.id == material_id)
        .execution_options(include_deleted=True)
        .with_for_update()
    )
    if material is None:
        # Already purged by a prior/concurrent run -- idempotent no-op.
        return "skipped"
    if material.deleted_at is None or material.deleted_at > cutoff:
        # Restored, or no longer past the boundary, since the candidate scan.
        return "skipped"
    if _material_has_retained_links(db, material_id):
        return "blocked"

    file_path = material.file_path
    owner_id = material.uploader_id
    deleted_at_before = material.deleted_at
    quarantine_token: str | None = None
    purge_job_id: UUID | None = None

    try:
        if file_path:
            try:
                quarantine_token = storage.quarantine(file_path)
            except FileNotFoundError:
                quarantine_token = None

        if quarantine_token is not None:
            purge_job_id = uuid4()
            db.add(
                PurgeJob(
                    id=purge_job_id,
                    material_id=material_id,
                    quarantine_token=quarantine_token,
                    status="pending_finalize",
                )
            )

        AuditService.record(
            db,
            AuditEventCreate(
                request_id=resolved_request_id,
                actor=_audit_actor(actor),
                action="purge.requested",
                entity=AuditEntity(
                    type="study_material",
                    id=str(material_id),
                    owner_id=owner_id,
                ),
                outcome="success",
                changes={},
                metadata={"deleted_at": deleted_at_before.isoformat()},
            ),
        )
        db.execute(delete(StudyMaterial).where(StudyMaterial.id == material_id))
        AuditService.record(
            db,
            AuditEventCreate(
                request_id=resolved_request_id,
                actor=_audit_actor(actor),
                action="purge.completed",
                entity=AuditEntity(
                    type="study_material",
                    id=str(material_id),
                    owner_id=owner_id,
                ),
                outcome="success",
                changes={},
                metadata={
                    "deleted_at": deleted_at_before.isoformat(),
                    "quarantined": quarantine_token is not None,
                },
            ),
        )
        db.commit()
    except Exception:
        db.rollback()
        if quarantine_token is not None:
            storage.restore_from_quarantine(quarantine_token)
        raise

    if quarantine_token is not None:
        storage.finalize_purge(quarantine_token)
        assert purge_job_id is not None
        _mark_purge_job_completed(db, purge_job_id)
    return "purged"


def apply_purge(
    db: Session,
    actor: Actor,
    *,
    batch_limit: int = DEFAULT_PURGE_BATCH_LIMIT,
    storage: FileStorage = material_file_storage,
    request_id: str | None = None,
) -> PurgeReport:
    """Permanently purge eligible, link-free materials, bounded to one batch.

    Admin-only (`Permission.PURGE_DELETED_DATA`). For each eligible material:
    record a `purge.requested` audit event, atomically quarantine its file,
    hard-delete the `StudyMaterial` row, record a `purge.completed` audit
    event, and commit -- all in one database transaction per material. Only
    after that transaction commits is the quarantined file permanently
    removed (`finalize_purge`). If any step before commit fails, the
    transaction rolls back (the row and its `deleted_at` are left exactly as
    they were) and the file is moved back out of quarantine to its original
    active path, so a failed purge never loses or double-purges data.

    Raises on the first unexpected failure rather than silently continuing
    the batch, so a caller (the CLI script) sees a non-zero exit and can
    retry -- retrying is safe because already-purged rows simply won't be
    selected again, and a partially-attempted material is left exactly as it
    was before the attempt.
    """
    require_permission(actor, Permission.PURGE_DELETED_DATA)

    cutoff = _purge_cutoff()
    candidates = _eligible_material_rows(db, limit=batch_limit)
    resolved_request_id = (
        request_id or get_current_request_id() or new_correlation_id()
    )

    purged: list[UUID] = []
    blocked: list[UUID] = []
    for candidate in candidates:
        outcome = _attempt_purge_one(
            db, actor, storage, candidate.id, cutoff, resolved_request_id
        )
        if outcome == "purged":
            purged.append(candidate.id)
        elif outcome == "blocked":
            blocked.append(candidate.id)

    return PurgeReport(
        action="apply",
        eligible_ids=tuple(candidate.id for candidate in candidates),
        purged_ids=tuple(purged),
        blocked_ids=tuple(blocked),
    )


def reconcile_pending_purge_jobs(
    db: Session,
    actor: Actor,
    *,
    storage: FileStorage = material_file_storage,
) -> ReconcileReport:
    """Finish any purge whose `finalize_purge()` call never ran.

    `_attempt_purge_one` commits the quarantine+hard-delete+ledger-insert as
    one transaction, then calls `storage.finalize_purge()` outside that
    transaction, then marks the ledger row completed. If the process dies
    in that window -- or between `finalize_purge()` succeeding and the
    completion update committing -- the ledger row is left
    `status="pending_finalize"`: a durable receipt naming exactly which
    quarantined file still needs to be permanently removed, so it is never
    silently stranded with no `StudyMaterial` row left for `plan_purge`/
    `apply_purge` to ever find again.

    Admin-only (`Permission.PURGE_DELETED_DATA`), same as `apply_purge`.
    Safe to run repeatedly and safe to run with nothing pending:
    `LocalFileStorage.finalize_purge` unlinks with `missing_ok=True`, so
    re-finalizing an already-removed file (e.g. because `finalize_purge`
    itself had already succeeded before the crash) is a no-op, and a run
    that finds no `pending_finalize` rows does nothing at all.
    """
    require_permission(actor, Permission.PURGE_DELETED_DATA)

    pending_jobs = db.scalars(
        select(PurgeJob)
        .where(PurgeJob.status == "pending_finalize")
        .order_by(PurgeJob.created_at, PurgeJob.id)
        .with_for_update()
    ).all()

    reconciled: list[UUID] = []
    for job in pending_jobs:
        storage.finalize_purge(job.quarantine_token)
        _mark_purge_job_completed(db, job.id)
        reconciled.append(job.material_id)

    return ReconcileReport(reconciled_material_ids=tuple(reconciled))


# ---------------------------------------------------------------------------
# Restricted AI payload expiry (AI-004)
#
# `CANONICAL_PROJECT_SPEC.md` §6.3: "Restricted raw AI prompts and retrieved
# context are retained for 30 days after the generation job completes, then
# purged through the governed lifecycle."
#
# This is deliberately a *separate* selector and a separate report rather than
# a widening of `_eligible_material_rows`. The material purge path's narrowness
# is the thing that makes its safety argument short enough to verify: it emits
# exactly one hardcoded `delete(StudyMaterial)` and reads only
# `Question`/`FlashcardDeck`/`TopicBrief` to check links. Threading a second
# entity type through that path would turn it into a generic dispatcher, and a
# generic dispatcher is exactly what the change contract forbids with "Purge is
# allowlisted, not generic."
#
# So the allowlist grows by one explicitly-named member with its own
# hardcoded delete, and `User`/`Exam`/`Question`/`Topic`/`Submission`/
# `SubmissionAnswer`/`audit_events` remain unreachable from either path -- see
# `test_purge_service_source_never_deletes_protected_models`, which asserts
# that over this module's whole source.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RestrictedPayloadPurgeReport:
    action: Literal["plan", "apply"]
    entity: str = "ai_restricted_payload"
    eligible_ids: tuple[UUID, ...] = ()
    purged_ids: tuple[UUID, ...] = ()

    @property
    def eligible_count(self) -> int:
        return len(self.eligible_ids)

    @property
    def purged_count(self) -> int:
        return len(self.purged_ids)


def _expired_restricted_payloads(
    db: Session, *, limit: int | None
) -> list[tuple[AIRestrictedPayload, UUID]]:
    """Payloads past their stamped §6.3 boundary, oldest first.

    Selects on the stored `expires_at` rather than recomputing
    `created_at + 30 days`, so the retention decision that actually applied
    to a given row governs it even if the constant later changes.

    The parent job's `owner_id` is joined in rather than looked up per row:
    the audit contract requires an owner on a purge event, and fetching it
    inside the purge loop would be exactly the query-in-loop pattern
    `architecture-guard` rejects.
    """
    statement = (
        select(AIRestrictedPayload, AIGenerationJob.owner_id)
        .join(AIGenerationJob, AIGenerationJob.id == AIRestrictedPayload.job_id)
        .where(AIRestrictedPayload.expires_at <= datetime.now(timezone.utc))
        .order_by(AIRestrictedPayload.expires_at, AIRestrictedPayload.id)
    )
    if limit is not None:
        statement = statement.limit(limit)
    return [(row[0], row[1]) for row in db.execute(statement).all()]


def plan_restricted_payload_purge(
    db: Session, *, batch_limit: int | None = None
) -> RestrictedPayloadPurgeReport:
    """Dry run: which restricted AI payloads are past their retention window.

    Read-only: no row is mutated and no audit event is written.
    """
    return RestrictedPayloadPurgeReport(
        action="plan",
        eligible_ids=tuple(
            payload.id
            for payload, _owner_id in _expired_restricted_payloads(
                db, limit=batch_limit
            )
        ),
    )



def _purge_one_restricted_payload(
    db: Session,
    actor: Actor,
    *,
    payload_id: UUID,
    job_id: UUID,
    owner_id: UUID,
    expires_at: str,
    resolved_request_id: str,
) -> None:
    """Audit and delete exactly one expired payload, as one transaction.

    Extracted from `apply_restricted_payload_purge`'s loop for the same
    reason `_attempt_purge_one` is: the per-item work issues statements, and
    `architecture-guard`'s `backend.query-in-loop` rule correctly rejects
    that shape inline. Keeping one transaction per payload also means a
    failure part-way through a batch leaves earlier payloads purged and
    audited, and later ones untouched -- never a deleted row with no audit
    event, nor an audit event for a row that still exists.
    """
    try:
        AuditService.record(
            db,
            AuditEventCreate(
                request_id=resolved_request_id,
                actor=_audit_actor(actor),
                action="purge.completed",
                entity=AuditEntity(
                    type="ai_restricted_payload",
                    id=str(payload_id),
                    owner_id=owner_id,
                ),
                outcome="success",
                changes={},
                # The parent job id is what keeps this event interpretable:
                # once the payload row is gone its own id names nothing, and
                # the surviving job is the only remaining handle on what was
                # purged.
                metadata={"expires_at": expires_at, "job_id": str(job_id)},
            ),
        )
        db.execute(
            delete(AIRestrictedPayload).where(AIRestrictedPayload.id == payload_id)
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


def apply_restricted_payload_purge(
    db: Session,
    actor: Actor,
    *,
    batch_limit: int = DEFAULT_PURGE_BATCH_LIMIT,
    request_id: str | None = None,
) -> RestrictedPayloadPurgeReport:
    """Permanently delete restricted AI payloads past their §6.3 window.

    Admin-only, bounded, audited, and idempotent, matching `apply_purge`.
    Simpler than the material path because there is no file and no cascade
    to consider: the row *is* the sensitive data, nothing references it, and
    the parent `AIGenerationJob` deliberately survives it -- §6.3 keeps the
    redacted metadata (prompt version, provider/model, usage, cost, latency,
    reviewer, outcome) "while the parent business record exists" and expires
    only the raw prompt and output.

    Each payload is deleted and audited in one transaction, so a crash can
    never leave a deleted payload unaudited or an audit event describing a
    row that still exists.
    """
    require_permission(actor, Permission.PURGE_DELETED_DATA)

    resolved_request_id = (
        request_id or get_current_request_id() or new_correlation_id()
    )
    candidates = _expired_restricted_payloads(db, limit=batch_limit)

    purged: list[UUID] = []
    for payload, owner_id in candidates:
        _purge_one_restricted_payload(
            db,
            actor,
            payload_id=payload.id,
            job_id=payload.job_id,
            owner_id=owner_id,
            expires_at=payload.expires_at.isoformat(),
            resolved_request_id=resolved_request_id,
        )
        purged.append(payload.id)

    return RestrictedPayloadPurgeReport(
        action="apply",
        eligible_ids=tuple(payload.id for payload, _owner_id in candidates),
        purged_ids=tuple(purged),
    )
