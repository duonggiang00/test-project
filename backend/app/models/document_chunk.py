import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    material_id = Column(
        UUID(as_uuid=True),
        ForeignKey("study_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
