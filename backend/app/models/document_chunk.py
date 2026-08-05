from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.db.base import Base
import uuid
from sqlalchemy.ext.compiler import compiles

@compiles(Vector, 'postgresql')
def compile_vector(element, compiler, **kw):
    return "VARCHAR"

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("study_materials.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
