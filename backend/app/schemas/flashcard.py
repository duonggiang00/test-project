from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

# Flashcard Deck Schemas
class FlashcardDeckBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    topic_id: UUID

class FlashcardDeckCreate(FlashcardDeckBase):
    pass

class FlashcardDeckUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class FlashcardDeckResponse(FlashcardDeckBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Flashcard Schemas
class FlashcardBase(BaseModel):
    front_content: str
    back_content: str
    order_index: int = 0
    deck_id: UUID

class FlashcardCreate(FlashcardBase):
    pass

class FlashcardUpdate(BaseModel):
    front_content: Optional[str] = None
    back_content: Optional[str] = None
    order_index: Optional[int] = None

class FlashcardResponse(FlashcardBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FlashcardDeckWithCardsResponse(FlashcardDeckResponse):
    flashcards: List[FlashcardResponse] = []
    model_config = ConfigDict(from_attributes=True)

# Topic Brief Schemas
class TopicBriefUpdate(BaseModel):
    brief_content: str
    brief_ai_generated: bool = False

# Flashcard Progress Schemas
class FlashcardReviewSubmit(BaseModel):
    rating: str = Field(..., description="EASY, GOOD, HARD, or AGAIN")

class FlashcardProgressResponse(BaseModel):
    id: UUID
    student_id: UUID
    flashcard_id: UUID
    box_level: int
    next_review_at: datetime
    last_reviewed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
