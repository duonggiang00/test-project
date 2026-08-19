"""Add restricted storage for rendered AI prompts and raw provider output.

Revision ID: e7b21c9d4a83
Revises: c4e1a70b58d9
Create Date: 2026-08-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7b21c9d4a83"
down_revision: Union[str, Sequence[str], None] = "c4e1a70b58d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_restricted_payloads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("rendered_prompt", sa.Text(), nullable=False),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["ai_generation_jobs.id"],
            name="ai_restricted_payloads_job_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_ai_restricted_payloads_job_id",
        "ai_restricted_payloads",
        ["job_id"],
        unique=True,
    )
    op.create_index(
        "ix_ai_restricted_payloads_expires_at",
        "ai_restricted_payloads",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the table unconditionally.

    Unlike the soft-delete (`f9f952e6df1a`) and AI-review-state
    (`c4e1a70b58d9`) downgrades, this one does not refuse while rows exist.
    Those guards protect *logical state a user could still act on* -- a
    pending deletion to restore, a review decision to honour. These rows are
    the opposite: sensitive raw prompts under a §6.3 data-minimization clock
    whose whole purpose is to stop existing. Discarding them early is the
    safe direction, and the surviving `audit_events` rows keep the redacted
    §2.4 projection (prompt version, provider/model, usage, cost, latency,
    reviewer, outcome) that makes each generation traceable without them.
    """
    op.drop_index(
        "ix_ai_restricted_payloads_expires_at", table_name="ai_restricted_payloads"
    )
    op.drop_index(
        "uq_ai_restricted_payloads_job_id", table_name="ai_restricted_payloads"
    )
    op.drop_table("ai_restricted_payloads")
