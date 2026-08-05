from pydantic import BaseModel, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)

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
