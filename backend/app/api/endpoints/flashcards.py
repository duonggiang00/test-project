from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from app.db.session import get_db
from app.schemas.flashcard import (
    FlashcardDeckCreate, FlashcardDeckUpdate, FlashcardDeckResponse, FlashcardDeckWithCardsResponse,
    FlashcardCreate, FlashcardUpdate, FlashcardResponse, FlashcardReviewSubmit
)
from app.schemas.topic import TopicBriefUpdate
from app.api.deps import get_current_active_teacher, get_current_active_user
from fastapi import BackgroundTasks
from app.services.ai_service import mock_generate_topic_kit
from app.services.flashcard_service import FlashcardService
from pydantic import BaseModel
from app.core.exceptions import AppException

router = APIRouter()

class GenerateTopicKitRequest(BaseModel):
    material_id: UUID
    topic_id: UUID

# --- ADMIN / TEACHER ROUTES ---

@router.post("/ai/generate-topic-kit")
def generate_topic_kit_ai(
    request: GenerateTopicKitRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_active_teacher)
):
    background_tasks.add_task(mock_generate_topic_kit, str(request.material_id), str(request.topic_id))
    return {"message": "AI is generating topic brief and flashcards in the background"}

@router.put("/topics/{topic_id}/brief")
def update_topic_brief(
    topic_id: UUID,
    data: TopicBriefUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_teacher)
):
    FlashcardService.update_topic_brief(db, topic_id, data.brief_content, data.brief_ai_generated)
    return {"message": "Topic brief updated"}

@router.post("/decks", response_model=FlashcardDeckResponse)
def create_deck(
    deck: FlashcardDeckCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_teacher)
):
    return FlashcardService.create_deck(db, deck.model_dump())

@router.get("/topics/{topic_id}/decks", response_model=List[FlashcardDeckResponse])
def get_topic_decks(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    return FlashcardService.get_topic_decks(db, topic_id)

@router.get("/decks/{deck_id}", response_model=FlashcardDeckWithCardsResponse)
def get_deck(
    deck_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    return FlashcardService.get_deck(db, deck_id)

@router.post("/decks/{deck_id}/cards", response_model=FlashcardResponse)
def create_card(
    deck_id: UUID,
    card: FlashcardCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_teacher)
):
    return FlashcardService.create_card(db, deck_id, card.model_dump())

# --- STUDENT ROUTES (SPACED REPETITION) ---

@router.get("/student/decks/{deck_id}/study", response_model=List[FlashcardResponse])
def get_study_cards(
    deck_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "student":
        raise AppException(status_code=403, error_code="FORBIDDEN", detail="Only students can study")
    
    return FlashcardService.get_study_cards(db, deck_id, current_user.id)

@router.post("/student/cards/{card_id}/review")
def review_card(
    card_id: UUID,
    review: FlashcardReviewSubmit,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role != "student":
        raise AppException(status_code=403, error_code="FORBIDDEN", detail="Only students can study")
        
    return FlashcardService.review_card(db, card_id, current_user.id, review.rating)
