from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List, Optional, Dict, Any
from app.models.enums import QuestionType, DifficultyLevel

class OptionBase(BaseModel):
    content: str
    is_correct: bool

class QuestionBase(BaseModel):
    content: str
    points: float = 1.0
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    topic_id: Optional[UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    options: List[OptionBase] = []

class QuestionUpdate(BaseModel):
    content: Optional[str] = None
    points: Optional[float] = None
    question_type: Optional[QuestionType] = None
    difficulty: Optional[DifficultyLevel] = None
    topic_id: Optional[UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    options: Optional[List[OptionBase]] = None

class OptionResponse(BaseModel):
    id: UUID
    content: str
    is_correct: bool
    
    model_config = ConfigDict(from_attributes=True)

class QuestionResponse(BaseModel):
    id: UUID
    content: str
    is_ai_generated: bool
    points: float
    question_type: QuestionType
    difficulty: DifficultyLevel
    topic_id: Optional[UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    options: List[OptionResponse]

    model_config = ConfigDict(from_attributes=True)

class QuestionBulkCreate(BaseModel):
    question_ids: List[UUID]
