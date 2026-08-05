from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class ExamBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = 60
    is_published: bool = False
    topic_id: Optional[UUID] = None

class ExamCreate(ExamBase):
    pass

class ExamUpdate(ExamBase):
    pass

class ExamResponse(ExamBase):
    id: UUID
    creator_id: UUID
    created_at: datetime
    topic_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

from app.schemas.question import QuestionResponse

class ExamDetailResponse(ExamResponse):
    questions: List[QuestionResponse]
