"""Add the missing single-choice question type.

Revision ID: a83c1d7e9f02
Revises: ca82f9a51d44
Create Date: 2026-08-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a83c1d7e9f02"
down_revision: Union[str, Sequence[str], None] = "ca82f9a51d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _current_labels(bind: sa.engine.Connection) -> tuple[str, ...]:
    return tuple(
        bind.execute(
            sa.text(
                "SELECT pg_enum.enumlabel "
                "FROM pg_enum "
                "JOIN pg_type ON pg_type.oid = pg_enum.enumtypid "
                "JOIN pg_namespace ON pg_namespace.oid = pg_type.typnamespace "
                "WHERE pg_namespace.nspname = 'public' "
                "AND pg_type.typname = 'questiontype' "
                "ORDER BY pg_enum.enumsortorder"
            )
        ).scalars()
    )


def _assert_question_type_column_contract(bind: sa.engine.Connection) -> None:
    definition = bind.execute(
        sa.text(
            "SELECT data_type, udt_schema, udt_name, is_nullable, "
            "column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = 'questions' "
            "AND column_name = 'question_type'"
        )
    ).one_or_none()
    expected = (
        "USER-DEFINED",
        "public",
        "questiontype",
        "NO",
        "'MULTIPLE_CHOICE'::questiontype",
    )
    if definition != expected:
        raise RuntimeError(
            "Cannot migrate SINGLE_CHOICE because public.questions.question_type "
            "does not match the expected column contract"
        )


def _replace_questiontype(
    bind: sa.engine.Connection,
    labels: tuple[str, ...],
    temporary_name: str,
) -> None:
    replacement = postgresql.ENUM(
        *labels,
        name=temporary_name,
        schema="public",
    )
    replacement.create(bind, checkfirst=False)
    op.execute(
        "ALTER TABLE public.questions "
        "ALTER COLUMN question_type DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE public.questions ALTER COLUMN question_type "
        f"TYPE public.{temporary_name} "
        f"USING question_type::text::public.{temporary_name}"
    )
    op.execute("DROP TYPE public.questiontype")
    op.execute(
        f"ALTER TYPE public.{temporary_name} RENAME TO questiontype"
    )
    op.execute(
        "ALTER TABLE public.questions ALTER COLUMN question_type "
        "SET DEFAULT 'MULTIPLE_CHOICE'::public.questiontype"
    )


def upgrade() -> None:
    bind = op.get_bind()
    _assert_question_type_column_contract(bind)
    current_labels = _current_labels(bind)
    expected_labels = (
        "MULTIPLE_CHOICE",
        "MATCHING",
        "FILL_IN_BLANK",
    )
    if current_labels != expected_labels:
        raise RuntimeError(
            "Cannot add SINGLE_CHOICE because public.questiontype does not "
            "match the expected pre-migration label set"
        )
    op.execute(
        "ALTER TYPE public.questiontype ADD VALUE "
        "'SINGLE_CHOICE' BEFORE 'MULTIPLE_CHOICE'"
    )


def downgrade() -> None:
    bind = op.get_bind()
    _assert_question_type_column_contract(bind)
    current_labels = _current_labels(bind)
    expected_labels = (
        "SINGLE_CHOICE",
        "MULTIPLE_CHOICE",
        "MATCHING",
        "FILL_IN_BLANK",
    )
    if current_labels != expected_labels:
        raise RuntimeError(
            "Cannot remove SINGLE_CHOICE because public.questiontype does not "
            "match the expected canonical label set"
        )
    single_choice_exists = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM public.questions "
            "WHERE question_type::text = 'SINGLE_CHOICE'"
            ")"
        )
    ).scalar_one()
    if single_choice_exists:
        raise RuntimeError(
            "Cannot downgrade questiontype while SINGLE_CHOICE rows exist; "
            "remove or convert those rows explicitly first"
        )

    _replace_questiontype(
        bind,
        ("MULTIPLE_CHOICE", "MATCHING", "FILL_IN_BLANK"),
        "questiontype_without_single_choice",
    )
