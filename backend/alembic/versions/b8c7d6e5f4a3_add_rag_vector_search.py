"""Require pgvector and add indexes for semantic and lexical retrieval.

The previous document-chunk migration could leave an installation with a
text-compatible embedding column when the Vector compiler was overridden. This
revision makes the runtime schema authoritative without dropping the shared
pgvector extension on downgrade.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c7d6e5f4a3"
down_revision: Union[str, Sequence[str], None] = "a74c9d2e6f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Do not swallow this error: a missing extension must stop the migration
    # before any index or column change can leave a partial schema.
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    op.execute(
        sa.text(
            "ALTER TABLE document_chunks "
            "ALTER COLUMN embedding TYPE vector(1536) "
            "USING embedding::vector(1536)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_material_id "
            "ON document_chunks (material_id)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
            "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_content_fts "
            "ON document_chunks USING gin (to_tsvector('simple', content))"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_document_chunks_content_fts"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_document_chunks_material_id"))
