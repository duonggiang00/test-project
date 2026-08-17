from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class MaterialResponse(BaseModel):
    id: UUID
    title: str
    file_type: str
    ai_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentChunkResponse(BaseModel):
    id: UUID
    content: str
    
    model_config = ConfigDict(from_attributes=True)

class MaterialDetailResponse(MaterialResponse):
    chunks: List[DocumentChunkResponse] = []

class GenerateQuestionsRequest(BaseModel):
    question_types: List[str]
    count: int = 5
    difficulty: str = "MEDIUM"

class OptionSchema(BaseModel):
    content: str
    is_correct: bool

class QuestionSchema(BaseModel):
    type: str
    content: str
    points: int = 1
    difficulty: str = "MEDIUM"
    source_reference: Optional[str] = None
    explanation: Optional[str] = None
    options: List[OptionSchema] = []
    metadata_json: Optional[dict] = None

class SaveQuestionsRequest(BaseModel):
    questions: List[QuestionSchema]

class GenerateFlashcardsRequest(BaseModel):
    count: int = 10

class FlashcardSchema(BaseModel):
    term: str
    definition: str
    source_reference: Optional[str] = None
    explanation: Optional[str] = None

class SaveFlashcardsRequest(BaseModel):
    title: str
    topic_id: Optional[str] = None
    flashcards: List[FlashcardSchema]

class SaveTopicBriefRequest(BaseModel):
    title: str
    content: str
    topic_id: Optional[str] = None
