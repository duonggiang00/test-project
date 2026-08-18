"""Add AI generation review state and advisory grade suggestions.

Revision ID: c4e1a70b58d9
Revises: 1dfa8dca16d5
Create Date: 2026-08-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e1a70b58d9"
down_revision: Union[str, Sequence[str], None] = "1dfa8dca16d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_generation_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("material_id", sa.UUID(), nullable=False),
        sa.Column("use_case", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="requested",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "draft_payload",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("reviewer_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ("
            "'requested', 'processing', 'generated', 'awaiting_review', "
            "'approved', 'rejected', 'published', 'failed')",
            name="ck_ai_generation_jobs_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_ai_generation_jobs_version"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="ai_generation_jobs_owner_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["study_materials.id"],
            name="ai_generation_jobs_material_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name="ai_generation_jobs_reviewer_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_generation_jobs_owner_id",
        "ai_generation_jobs",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_generation_jobs_material_id",
        "ai_generation_jobs",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_generation_jobs_status",
        "ai_generation_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_ai_generation_jobs_reviewer_id",
        "ai_generation_jobs",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_generation_jobs_owner_status",
        "ai_generation_jobs",
        ["owner_id", "status"],
        unique=False,
    )

    op.create_table(
        "ai_grade_suggestions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("submission_answer_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="awaiting_review",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("suggested_points", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('awaiting_review', 'approved', 'rejected')",
            name="ck_ai_grade_suggestions_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_ai_grade_suggestions_version"),
        sa.ForeignKeyConstraint(
            ["submission_answer_id"],
            ["submission_answers.id"],
            name="ai_grade_suggestions_submission_answer_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="ai_grade_suggestions_owner_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name="ai_grade_suggestions_reviewer_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_grade_suggestions_submission_answer_id",
        "ai_grade_suggestions",
        ["submission_answer_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_grade_suggestions_owner_id",
        "ai_grade_suggestions",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_grade_suggestions_status",
        "ai_grade_suggestions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_ai_grade_suggestions_reviewer_id",
        "ai_grade_suggestions",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_grade_suggestions_answer_status",
        "ai_grade_suggestions",
        ["submission_answer_id", "status"],
        unique=False,
    )


def _assert_no_unreviewed_rows(bind: sa.engine.Connection) -> None:
    """Refuse the downgrade while any review state would be destroyed.

    Dropping these tables discards the record of which AI content was
    approved, by whom, and which grade suggestions are still pending -- the
    same class of destructive logical-state loss that the soft-delete
    downgrade guard (`f9f952e6df1a`) refuses.
    """
    pending: dict[str, int] = {}
    for table in ("ai_generation_jobs", "ai_grade_suggestions"):
        count = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM public.{table}")
        ).scalar_one()
        if count:
            pending[table] = count
    if pending:
        raise RuntimeError(
            "Cannot downgrade AI review state while rows exist; export or "
            f"resolve them first: {pending!r}"
        )


def downgrade() -> None:
    bind = op.get_bind()
    _assert_no_unreviewed_rows(bind)

    op.drop_index(
        "ix_ai_grade_suggestions_answer_status", table_name="ai_grade_suggestions"
    )
    op.drop_index(
        "ix_ai_grade_suggestions_reviewer_id", table_name="ai_grade_suggestions"
    )
    op.drop_index("ix_ai_grade_suggestions_status", table_name="ai_grade_suggestions")
    op.drop_index("ix_ai_grade_suggestions_owner_id", table_name="ai_grade_suggestions")
    op.drop_index(
        "ix_ai_grade_suggestions_submission_answer_id",
        table_name="ai_grade_suggestions",
    )
    op.drop_table("ai_grade_suggestions")

    op.drop_index(
        "ix_ai_generation_jobs_owner_status", table_name="ai_generation_jobs"
    )
    op.drop_index(
        "ix_ai_generation_jobs_reviewer_id", table_name="ai_generation_jobs"
    )
    op.drop_index("ix_ai_generation_jobs_status", table_name="ai_generation_jobs")
    op.drop_index("ix_ai_generation_jobs_material_id", table_name="ai_generation_jobs")
    op.drop_index("ix_ai_generation_jobs_owner_id", table_name="ai_generation_jobs")
    op.drop_table("ai_generation_jobs")
