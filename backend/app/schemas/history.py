from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class SubmissionHistoryItem(BaseModel):
    id: UUID
    exam_id: UUID
    exam_title: Optional[str] = ""
    student_id: UUID
    student_name: Optional[str] = ""
    student_email: Optional[str] = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_score: float
    status: str

    model_config = ConfigDict(from_attributes=True)

class SubmissionAnswerDetail(BaseModel):
    question_id: UUID
    question_content: str
    answer_data: Optional[dict] = None
    is_correct: Optional[bool] = None
    points_awarded: float
    # The question's maximum, so a reviewer can be shown (and the client can
    # pre-validate) the legal range for a correction. Already loaded by
    # `HistoryService.get_submission_detail`; it was simply discarded before.
    max_points: Optional[float] = None
    # Manual-correction trail (GRADE-001). Null on an untouched answer.
    override_reason: Optional[str] = None
    overridden_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GradeOverrideRequest(BaseModel):
    """A teacher's correction of one answer's score.

    `points_awarded` is bounded server-side against the question's own
    `points`; `is_correct` is deliberately absent because it is derived, and
    `total_score` is absent because it is recomputed from the answers -- a
    client can neither assert a total nor desynchronise it from its parts.
    """

    points_awarded: float = Field(ge=0)
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, reason: str) -> str:
        cleaned = reason.strip()
        if not cleaned:
            raise ValueError("reason must not be blank")
        return cleaned

class SubmissionDetailResponse(BaseModel):
    id: UUID
    exam_id: UUID
    exam_title: str
    student_id: UUID
    student_name: str
    student_email: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_score: float
    status: str
    answers: List[SubmissionAnswerDetail]

    model_config = ConfigDict(from_attributes=True)
