"""Persisted review state for AI-generated content (AI-002) and advisory
AI grade suggestions (AI-009).

`CANONICAL_PROJECT_SPEC.md` §9.2 fixes the approved state machine:

    requested -> processing -> generated -> awaiting_review
              -> approved | rejected -> published

with "No direct `generated -> published` transition is allowed." Before this
module, `Question.is_ai_generated`/`TopicBrief.is_ai_generated` were plain
booleans and `StudyMaterial.ai_status` described *processing*, not approval,
so none of those transitions could be expressed -- and `material_service`'s
`save_*` methods could persist generated content on a single click with no
recorded reviewer, rejection path, or reviewable draft.

Transitions are enforced in `app/services/ai_generation_service.py` by the
`ALLOWED_TRANSITIONS` allowlist combined with the `version` column
(optimistic concurrency) and `SELECT ... FOR UPDATE` row locking, all three
of which the AI-001-009 change contract requires.

ADR-0006's supersession clause is load-bearing here: any future automatic
publishing or final AI grading needs a NEW approved ADR, so neither this
model nor its service may ever expose an auto-publish or auto-apply path.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base

# The canonical states from CANONICAL_PROJECT_SPEC.md §9.2, plus `failed`,
# which the change contract allows "from execution states".
AI_JOB_STATUSES = (
    "requested",
    "processing",
    "generated",
    "awaiting_review",
    "approved",
    "rejected",
    "published",
    "failed",
)

# An advisory grade suggestion is reviewable or resolved -- never "applied"
# without an explicit owner/admin approval (AI-009).
AI_GRADE_SUGGESTION_STATUSES = (
    "awaiting_review",
    "approved",
    "rejected",
)


class AIGenerationJob(Base):
    """One reviewable unit of AI-generated content.

    `draft_payload` holds the *business* draft under review (the proposed
    questions/flashcards/brief) so a reviewer can inspect it before anything
    is written into the live tables. It deliberately does NOT hold the
    rendered prompt or the raw provider response: the change contract puts
    those in a separate restricted payload record, which is AI-003/AI-004
    scope.

    `reviewer_id` is set only on approve/reject and is always taken from the
    acting request's actor, never copied from `owner_id` -- the change
    contract states "The reviewer cannot be inferred from the generation
    actor."
    """

    __tablename__ = "ai_generation_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'requested', 'processing', 'generated', 'awaiting_review', "
            "'approved', 'rejected', 'published', 'failed')",
            name="ck_ai_generation_jobs_status",
        ),
        CheckConstraint("version >= 1", name="ck_ai_generation_jobs_version"),
        Index("ix_ai_generation_jobs_owner_status", "owner_id", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="ai_generation_jobs_owner_id_fkey",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    material_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "study_materials.id",
            name="ai_generation_jobs_material_id_fkey",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    use_case = Column(String(64), nullable=False)
    status = Column(
        String(32),
        nullable=False,
        default="requested",
        server_default="requested",
        index=True,
    )
    # Optimistic-concurrency counter, bumped on every accepted transition.
    version = Column(Integer, nullable=False, default=1, server_default="1")
    draft_payload = Column(JSONB, nullable=True)
    failure_code = Column(String(64), nullable=True)
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="ai_generation_jobs_reviewer_id_fkey",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)


class AIGradeSuggestion(Base):
    """An advisory AI grade suggestion for one submission answer (AI-009).

    Created `awaiting_review` and immutable thereafter apart from its own
    review fields: creating or completing a suggestion can never change
    awarded points, submission totals, or result release. Only an explicit
    owner/admin approval applies it, atomically with an audit event.

    The existing deterministic `GradingService` scoring is unaffected and is
    NOT reclassified as AI grading -- the change contract is explicit that
    "Existing deterministic objective scoring remains automatic and is not
    reclassified as AI grading."
    """

    __tablename__ = "ai_grade_suggestions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting_review', 'approved', 'rejected')",
            name="ck_ai_grade_suggestions_status",
        ),
        CheckConstraint("version >= 1", name="ck_ai_grade_suggestions_version"),
        Index(
            "ix_ai_grade_suggestions_answer_status",
            "submission_answer_id",
            "status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_answer_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "submission_answers.id",
            name="ai_grade_suggestions_submission_answer_id_fkey",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="ai_grade_suggestions_owner_id_fkey",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    status = Column(
        String(32),
        nullable=False,
        default="awaiting_review",
        server_default="awaiting_review",
        index=True,
    )
    version = Column(Integer, nullable=False, default=1, server_default="1")
    suggested_points = Column(Integer, nullable=False)
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="ai_grade_suggestions_reviewer_id_fkey",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
