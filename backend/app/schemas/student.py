from pydantic import BaseModel, ConfigDict, model_validator
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime

class StudentOptionResponse(BaseModel):
    id: UUID
    content: str
    # is_correct IS OMITTED DELIBERATELY!

    model_config = ConfigDict(from_attributes=True)


class StudentFillInBlankMetadataResponse(BaseModel):
    blank_count: int

    model_config = ConfigDict(extra="forbid")


class StudentMatchingMetadataResponse(BaseModel):
    left_options: List[str]
    right_options: List[str]

    model_config = ConfigDict(extra="forbid")


class StudentQuestionResponse(BaseModel):
    id: UUID
    content: str
    points: float
    question_type: str
    metadata_json: Optional[
        StudentFillInBlankMetadataResponse | StudentMatchingMetadataResponse
    ] = None
    options: List[StudentOptionResponse]

    model_config = ConfigDict(from_attributes=True)

class StudentExamResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    duration_minutes: int
    remaining_seconds: int
    questions: List[StudentQuestionResponse]
    
    model_config = ConfigDict(from_attributes=True)

class StudentExamListResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    duration_minutes: int
    topic_name: Optional[str] = None
    question_count: int = 0
    max_score: float = 0.0
    submission_status: Optional[str] = None # None, "in_progress", "submitted"
    total_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class AnswerInput(BaseModel):
    question_id: UUID
    answer_data: Optional[Dict[str, Any]] = None
    selected_option_id: Optional[UUID] = None

class SubmitExamRequest(BaseModel):
    answers: List[AnswerInput]

    @model_validator(mode="after")
    def reject_duplicate_question_answers(self) -> "SubmitExamRequest":
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each question may be answered at most once")
        return self

class SubmitExamResponse(BaseModel):
    submission_id: UUID
    total_score: float
    max_score: float

class StudentResultOptionResponse(StudentOptionResponse):
    is_correct: bool

class StudentExamResultAnswer(BaseModel):
    question_id: UUID
    content: str
    question_type: str
    metadata_json: Optional[Dict[str, Any]] = None
    options: List[StudentResultOptionResponse]
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
