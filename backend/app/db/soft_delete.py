"""Shared soft-delete columns and default-read query policy.

Governed aggregate roots (`User`, `Topic`, `Exam`, `Question`,
`StudyMaterial`) mix in `SoftDeleteMixin` to gain a timezone-aware
`deleted_at` and a `deleted_by_id` actor reference. A row is soft-deleted
when `deleted_at IS NOT NULL`.

Default session reads must exclude soft-deleted rows. This module registers
a single `do_orm_execute` listener on `Session` that applies a
`with_loader_criteria(<model>, deleted_at IS NULL)` filter to every mapped
class using the mixin, for every SELECT executed through any `Session`
instance. Restore/purge code paths (built in later phases) opt back in on a
per-statement basis with `execution_options(include_deleted=True)`; no other
mechanism bypasses the filter.

Cross-module dependency: because this filter is global, a soft-deleted
`Exam`/`Topic`/`Question` silently disappears from every default read --
including reads that join through it to reach `Submission` rows.
`AnalyticsService` (get_overview/get_score_stats/get_completion_status/
get_topic_performance), `HistoryService` (submission history/detail), and
`StudentService.get_exam_result` all join through or read `Exam`, so they
would silently lose visibility into retained submissions/grades if an
`Exam`/`Topic`/`Question` with live `Submission` rows were ever
soft-deleted -- violating the MVP retention policy
(`docs/spec/CANONICAL_PROJECT_SPEC.md` 6.3). This is currently prevented
only incidentally: `exam_service.delete_exam`, `topic_service.delete_topic`,
and `question_service._raise_if_question_is_retained` each block soft-delete
while retained records are linked (see the comments at those call sites).
If any of those guards is ever relaxed -- e.g. a future cascade-delete
option, mirroring `material_service.delete_material`'s `cascade`/
`keep_assets` flags -- the three services named above must be re-audited.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID as UUIDType

from sqlalchemy import Column, DateTime, ForeignKey, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, declared_attr, with_loader_criteria
from sqlalchemy.orm.session import ORMExecuteState

from app.db.base import Base

INCLUDE_DELETED_OPTION = "include_deleted"

# Shared 30-day recovery window: restore is eligible only while
# `deleted_at > now - RESTORE_WINDOW` (DATA-004). Permanent purge (a later
# phase) uses the complementary `deleted_at <= now - RESTORE_WINDOW` boundary
# so the two policies never disagree at the exact cutoff.
RESTORE_WINDOW = timedelta(days=30)


def is_restorable(deleted_at: datetime) -> bool:
    """True while a soft-deleted row is still inside the restore window."""
    return deleted_at > datetime.now(timezone.utc) - RESTORE_WINDOW


class SoftDeleteMixin:
    """Adds `deleted_at`/`deleted_by_id` to a declarative model.

    `deleted_by_id` gets a per-table foreign-key constraint name
    (`<table>_deleted_by_id_fkey`) to match this codebase's explicit-FK
    naming convention.
    """

    __tablename__: str  # provided by the concrete declarative model

    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    @declared_attr
    def deleted_by_id(cls):  # noqa: N805 - SQLAlchemy declared_attr convention
        return Column(
            UUID(as_uuid=True),
            ForeignKey(
                "users.id",
                name=f"{cls.__tablename__}_deleted_by_id_fkey",
                ondelete="SET NULL",
            ),
            nullable=True,
            index=True,
        )


def soft_delete(obj: Any, actor_id: UUIDType | None) -> None:
    """Mark `obj` deleted in place.

    Callers own commit/rollback (see
    `AuthorizationService.commit_with_admin_override`); this helper only
    mutates the in-session object.
    """
    obj.deleted_at = datetime.now(timezone.utc)
    obj.deleted_by_id = actor_id


@event.listens_for(Session, "do_orm_execute")
def _exclude_soft_deleted_rows(execute_state: ORMExecuteState) -> None:
    if not execute_state.is_select:
        return
    if execute_state.execution_options.get(INCLUDE_DELETED_OPTION, False):
        return
    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        if issubclass(model_class, SoftDeleteMixin):
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    model_class,
                    model_class.deleted_at.is_(None),
                    include_aliases=True,
                )
            )
