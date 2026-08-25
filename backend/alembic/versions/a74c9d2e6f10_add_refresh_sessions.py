"""Add active-user state and refresh-token sessions.

Revision ID: a74c9d2e6f10
Revises: b6d4f0a17c53
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a74c9d2e6f10"
down_revision: Union[str, Sequence[str], None] = "b6d4f0a17c53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "remember_me",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "char_length(token_hash) = 64",
            name="ck_refresh_sessions_token_hash_length",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_refresh_sessions_expiry_after_creation",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"],
            ["refresh_sessions.id"],
            name="refresh_sessions_replaced_by_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="refresh_sessions_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="refresh_sessions_pkey"),
    )
    op.create_index(
        "ix_refresh_sessions_expires_at",
        "refresh_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_sessions_family_active",
        "refresh_sessions",
        ["family_id", "revoked_at", "rotated_at"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_sessions_family_id",
        "refresh_sessions",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_sessions_revoked_at",
        "refresh_sessions",
        ["revoked_at"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_sessions_token_hash",
        "refresh_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_refresh_sessions_user_id",
        "refresh_sessions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_sessions_user_id", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_token_hash", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_revoked_at", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_family_id", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_family_active", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_expires_at", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_column("users", "is_active")
