from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime

class StudentOptionResponse(BaseModel):
    id: UUID
    content: str
    # is_correct IS OMITTED DELIBERATELY!

    model_config = ConfigDict(from_attributes=True)

class StudentQuestionResponse(BaseModel):
    id: UUID
    content: str
    points: float
    question_type: str
    metadata_json: Optional[Dict[str, Any]] = None
    options: List[StudentOptionResponse]

    model_config = ConfigDict(from_attributes=True)

class StudentExamResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    duration_minutes: int
    questions: List[StudentQuestionResponse]
    
    model_config = ConfigDict(from_attributes=True)

class StudentExamListResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    duration_minutes: int
    submission_status: Optional[str] = None # None, "in_progress", "submitted"
    total_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class AnswerInput(BaseModel):
    question_id: UUID
    answer_data: Optional[Dict[str, Any]] = None
    selected_option_id: Optional[UUID] = None

class SubmitExamRequest(BaseModel):
    answers: List[AnswerInput]

class SubmitExamResponse(BaseModel):
    submission_id: UUID
    total_score: float
    max_score: float

class StudentExamResultAnswer(BaseModel):
    question_id: UUID
    content: str
    question_type: str
    metadata_json: Optional[Dict[str, Any]] = None
    options: List[StudentOptionResponse]
    answer_data: Optional[Dict[str, Any]]
    is_correct: bool
    points_awarded: float
    points: float

    model_config = ConfigDict(from_attributes=True)

class StudentExamResultResponse(BaseModel):
    exam_id: UUID
    title: str
    total_score: float
    max_score: float
    correct_count: int
    incorrect_count: int
    time_taken_seconds: int
    answers: List[StudentExamResultAnswer]

    model_config = ConfigDict(from_attributes=True)
