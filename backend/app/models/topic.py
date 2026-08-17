from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid

class Topic(Base):
    __tablename__ = "topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="topics_owner_id_fkey",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    brief_content = Column(Text, nullable=True)
    brief_ai_generated = Column(Boolean, default=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Self-referential relationship for nested topics (e.g. Math -> Algebra)
    owner = relationship("User", foreign_keys=[owner_id])
    parent = relationship("Topic", remote_side=[id], back_populates="subtopics")
    subtopics = relationship("Topic", back_populates="parent", cascade="all, delete-orphan")
    
    exams = relationship("Exam", back_populates="topic")
    questions = relationship("Question", back_populates="topic")
    materials = relationship("StudyMaterial", back_populates="topic")
    briefs = relationship("TopicBrief", back_populates="topic", cascade="all, delete-orphan")
