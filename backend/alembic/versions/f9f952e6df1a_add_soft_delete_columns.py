"""Add soft-delete columns to governed aggregate roots.

Revision ID: f9f952e6df1a
Revises: a83c1d7e9f02
Create Date: 2026-08-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9f952e6df1a"
down_revision: Union[str, Sequence[str], None] = "a83c1d7e9f02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Governed delete-capable roots per the DATA-003 change contract.
SOFT_DELETE_TABLES = (
    "users",
    "topics",
    "exams",
    "questions",
    "study_materials",
)


def _fkey_name(table: str) -> str:
    return f"{table}_deleted_by_id_fkey"


def _deleted_at_index_name(table: str) -> str:
    return f"ix_{table}_deleted_at"


def _deleted_by_id_index_name(table: str) -> str:
    return f"ix_{table}_deleted_by_id"


def upgrade() -> None:
    for table in SOFT_DELETE_TABLES:
        op.add_column(
            table,
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("deleted_by_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            _fkey_name(table),
            table,
            "users",
            ["deleted_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            _deleted_at_index_name(table),
            table,
            ["deleted_at"],
        )
        op.create_index(
            _deleted_by_id_index_name(table),
            table,
            ["deleted_by_id"],
        )


def _assert_no_deleted_rows(bind: sa.engine.Connection) -> None:
    """Refuse the downgrade while any governed row is soft-deleted.

    Dropping these columns would silently discard logical deletion state,
    which the change contract's rollback rule explicitly forbids.
    """
    deleted_counts: dict[str, int] = {}
    for table in SOFT_DELETE_TABLES:
        count = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM public.{table} WHERE deleted_at IS NOT NULL")
        ).scalar_one()
        if count:
            deleted_counts[table] = count
    if deleted_counts:
        raise RuntimeError(
            "Cannot downgrade soft-delete columns while deleted rows exist; "
            f"restore or export them first: {deleted_counts!r}"
        )


def downgrade() -> None:
    bind = op.get_bind()
    _assert_no_deleted_rows(bind)

    for table in reversed(SOFT_DELETE_TABLES):
        op.drop_index(_deleted_by_id_index_name(table), table_name=table)
        op.drop_index(_deleted_at_index_name(table), table_name=table)
        op.drop_constraint(_fkey_name(table), table, type_="foreignkey")
        op.drop_column(table, "deleted_by_id")
        op.drop_column(table, "deleted_at")
