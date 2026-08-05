from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid
from sqlalchemy.sql import func
from app.models.enums import QuestionType, DifficultyLevel

class Exam(Base):
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False, default=60)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")
    topic = relationship("Topic", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("study_materials.id", ondelete="SET NULL"), nullable=True)
    
    question_type = Column(SQLAlchemyEnum(QuestionType), nullable=False, default=QuestionType.MULTIPLE_CHOICE)
    difficulty = Column(SQLAlchemyEnum(DifficultyLevel), nullable=False, default=DifficultyLevel.MEDIUM)
    
    content = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=True) # Used for MATCHING pairs, FILL_IN_BLANK words, etc.
    
    is_ai_generated = Column(Boolean, default=False)
    points = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    exam = relationship("Exam", back_populates="questions")
    topic = relationship("Topic", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    material = relationship("StudyMaterial")

class Option(Base):
    __tablename__ = "options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)

    question = relationship("Question", back_populates="options")
