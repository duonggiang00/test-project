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
from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.core.correlation import get_current_request_id, new_correlation_id
from app.core.file_storage import FileStorage, material_file_storage
from app.core.permissions import Actor, Permission, require_permission
from app.db.soft_delete import RESTORE_WINDOW
from app.models.exam import Question
from app.models.flashcard import FlashcardDeck
from app.models.material import StudyMaterial
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
    quarantine-audit-delete-audit-commit sequence as a single transaction.
    On any failure before commit, the transaction rolls back and the file
    (if quarantined) is moved back to its original active path before the
    exception propagates to the caller.
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

    try:
        if file_path:
            try:
                quarantine_token = storage.quarantine(file_path)
            except FileNotFoundError:
                quarantine_token = None

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
