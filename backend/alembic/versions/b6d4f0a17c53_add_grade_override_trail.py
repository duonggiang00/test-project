"""Add the manual grade-correction trail to submission answers.

Revision ID: b6d4f0a17c53
Revises: e7b21c9d4a83
Create Date: 2026-08-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6d4f0a17c53"
down_revision: Union[str, Sequence[str], None] = "e7b21c9d4a83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "submission_answers",
        sa.Column("override_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "submission_answers",
        sa.Column("overridden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "submission_answers",
        sa.Column("overridden_by_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "submission_answers_overridden_by_id_fkey",
        "submission_answers",
        "users",
        ["overridden_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_submission_answers_overridden_by_id",
        "submission_answers",
        ["overridden_by_id"],
        unique=False,
    )


def _assert_no_overridden_rows(bind: sa.engine.Connection) -> None:
    """Refuse the downgrade while any grade has been manually corrected.

    These columns are the only record of *why* a stored grade differs from
    what the automatic grader produced. Dropping them would leave the
    corrected `points_awarded` in place with no explanation attached to the
    row -- a silent loss of justification on a retained educational record.
    The audit event survives, but it deliberately carries no reason text
    (see the model docstring), so it cannot reconstruct this.
    """
    count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM public.submission_answers "
            "WHERE overridden_at IS NOT NULL"
        )
    ).scalar_one()
    if count:
        raise RuntimeError(
            "Cannot downgrade the grade-override trail while "
            f"{count} corrected answer(s) exist; export them first"
        )


def downgrade() -> None:
    bind = op.get_bind()
    _assert_no_overridden_rows(bind)

    op.drop_index(
        "ix_submission_answers_overridden_by_id",
        table_name="submission_answers",
    )
    op.drop_constraint(
        "submission_answers_overridden_by_id_fkey",
        "submission_answers",
        type_="foreignkey",
    )
    op.drop_column("submission_answers", "overridden_by_id")
    op.drop_column("submission_answers", "overridden_at")
    op.drop_column("submission_answers", "override_reason")
