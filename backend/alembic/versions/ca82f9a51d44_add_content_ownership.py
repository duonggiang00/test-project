"""Add explicit content ownership and owner-scope indexes.

Revision ID: ca82f9a51d44
Revises: b57c9a14d2e8
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ca82f9a51d44"
down_revision: Union[str, Sequence[str], None] = "b57c9a14d2e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "topics",
        sa.Column("owner_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("owner_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "topics_owner_id_fkey",
        "topics",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "questions_owner_id_fkey",
        "questions",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index("ix_topics_owner_id", "topics", ["owner_id"])
    op.create_index("ix_questions_owner_id", "questions", ["owner_id"])
    op.create_index("ix_exams_creator_id", "exams", ["creator_id"])
    op.create_index(
        "ix_study_materials_uploader_id",
        "study_materials",
        ["uploader_id"],
    )
    op.create_index("ix_questions_exam_id", "questions", ["exam_id"])
    op.create_index(
        "ix_flashcard_decks_topic_id",
        "flashcard_decks",
        ["topic_id"],
    )
    op.create_index("ix_flashcards_deck_id", "flashcards", ["deck_id"])
    op.create_index(
        "ix_topic_briefs_topic_id",
        "topic_briefs",
        ["topic_id"],
    )
    op.create_index(
        "ix_document_chunks_material_id",
        "document_chunks",
        ["material_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_material_id", table_name="document_chunks")
    op.drop_index("ix_topic_briefs_topic_id", table_name="topic_briefs")
    op.drop_index("ix_flashcards_deck_id", table_name="flashcards")
    op.drop_index("ix_flashcard_decks_topic_id", table_name="flashcard_decks")
    op.drop_index("ix_questions_exam_id", table_name="questions")
    op.drop_index(
        "ix_study_materials_uploader_id",
        table_name="study_materials",
    )
    op.drop_index("ix_exams_creator_id", table_name="exams")
    op.drop_index("ix_questions_owner_id", table_name="questions")
    op.drop_index("ix_topics_owner_id", table_name="topics")

    op.drop_constraint(
        "questions_owner_id_fkey",
        "questions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "topics_owner_id_fkey",
        "topics",
        type_="foreignkey",
    )
    op.drop_column("questions", "owner_id")
    op.drop_column("topics", "owner_id")
