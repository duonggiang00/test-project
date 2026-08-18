"""Add purge_jobs ledger for crash-window purge reconciliation.

Revision ID: 1dfa8dca16d5
Revises: f9f952e6df1a
Create Date: 2026-08-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1dfa8dca16d5"
down_revision: Union[str, Sequence[str], None] = "f9f952e6df1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purge_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("material_id", sa.UUID(), nullable=False),
        sa.Column("quarantine_token", sa.String(length=1024), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending_finalize",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending_finalize', 'completed')",
            name="ck_purge_jobs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purge_jobs_material_id", "purge_jobs", ["material_id"], unique=False
    )
    op.create_index(
        "ix_purge_jobs_status", "purge_jobs", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_purge_jobs_status", table_name="purge_jobs")
    op.drop_index("ix_purge_jobs_material_id", table_name="purge_jobs")
    op.drop_table("purge_jobs")
