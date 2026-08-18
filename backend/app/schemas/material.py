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

class GenerateFlashcardsRequest(BaseModel):
    count: int = 10

# `SaveQuestionsRequest`/`SaveFlashcardsRequest`/`SaveTopicBriefRequest` and
# their item schemas are deliberately gone (AI-002). They described a request
# body that wrote straight into Question/Flashcard/TopicBrief with no recorded
# reviewer, which CANONICAL_PROJECT_SPEC.md §9.2 forbids. Publication now
# reads its content from a reviewed `AIGenerationJob.draft_payload`; the draft
# item schemas live in `app/schemas/ai_generation.py`.
