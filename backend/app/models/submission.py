from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid
from sqlalchemy.sql import func

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    start_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    total_score = Column(Float, default=0)
    status = Column(String(20), default="in_progress")

    __table_args__ = (UniqueConstraint('exam_id', 'student_id', name='uq_exam_student'),)

    exam = relationship("Exam")
    student = relationship("User")
    answers = relationship("SubmissionAnswer", back_populates="submission", cascade="all, delete-orphan")

    @property
    def exam_title(self) -> str:
        return self.exam.title if self.exam else ""

    @property
    def student_name(self) -> str:
        if self.student:
            return self.student.full_name or self.student.email or ""
        return ""

    @property
    def student_email(self) -> str:
        return self.student.email if self.student else ""

class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"))
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"))
    
    # We no longer strictly tie this to a single Option ID because of Fill-in-blank or Matching
    answer_data = Column(JSONB, nullable=True) 
    
    is_correct = Column(Boolean)
    points_awarded = Column(Float, default=0.0)

    # GRADE-001 manual-correction trail. `override_reason` is free text a
    # teacher types, so it lives here rather than in the audit event:
    # `app.core.safe_payload` rejects any string containing a control
    # character (a newline is enough), an email, or a path-shaped token, so
    # routing a typed reason through `audit_events` would turn an ordinary
    # grade correction into a 500. The audit event keeps only safe scalars
    # and this row keeps the prose -- the same split AI-003/AI-004 uses for
    # rendered prompts.
    override_reason = Column(Text, nullable=True)
    overridden_at = Column(DateTime(timezone=True), nullable=True)
    overridden_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="submission_answers_overridden_by_id_fkey",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    __table_args__ = (UniqueConstraint('submission_id', 'question_id', name='uq_submission_question'),)

    submission = relationship("Submission", back_populates="answers")
