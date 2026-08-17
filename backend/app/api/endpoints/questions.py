from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.session import get_db
from app.models.user import User
from app.schemas.question import QuestionBase, QuestionResponse, QuestionUpdate
from app.services.question_service import QuestionService
from app.api.deps import get_current_active_teacher
from app.core.exceptions import AppException

router = APIRouter()

@router.get("", response_model=Page[QuestionResponse])
def read_questions(
    topic_id: Optional[UUID] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Get paginated question bank list with eager-loaded options and filters.
    """
    query = QuestionService.get_questions_query(
        db,
        current_user,
        topic_id,
        difficulty,
        search,
    )
    return paginate(db, query)

@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question_in: QuestionBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Create a standalone question bank question with options.
    """
    return QuestionService.create_question(db, question_in, current_user)

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return QuestionService.get_question(db, question_id, current_user)

@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: UUID,
    question_in: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return QuestionService.update_question(db, question_id, question_in, current_user)

@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    QuestionService.delete_question(db, question_id, current_user)
    return {"message": "Question deleted successfully", "id": str(question_id)}
