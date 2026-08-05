from fastapi import APIRouter, Depends, Query, status
from app.core.exceptions import AppException
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.session import get_db
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate, ExamResponse, ExamDetailResponse
from app.schemas.question import QuestionBulkCreate, QuestionBase, QuestionResponse
from app.services.exam_service import ExamService
from app.api.deps import get_current_active_teacher, get_current_user

router = APIRouter()

@router.get("", response_model=Page[ExamResponse])
def read_exams(
    search: Optional[str] = None,
    topic_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    query = ExamService.get_exams_query(db, search, topic_id)
    return paginate(db, query)

@router.post("", response_model=ExamResponse)
def create_exam(
    exam_in: ExamCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return ExamService.create_exam(db, exam_in, current_user.id)

@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: UUID,
    exam_in: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return ExamService.update_exam(db, exam_id, exam_in, current_user)

@router.delete("/{exam_id}", status_code=status.HTTP_200_OK)
def delete_exam(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Delete an exam. (Requires creator or admin authentication)
    """
    ExamService.delete_exam(db, exam_id, current_user)
    return {"message": "Exam deleted successfully", "id": str(exam_id)}

@router.get("/{exam_id}", response_model=ExamDetailResponse)
def get_exam(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return ExamService.get_exam(db, exam_id, current_user)

@router.post("/{exam_id}/questions", response_model=QuestionResponse)
def create_question_in_exam(
    exam_id: UUID,
    question_in: QuestionBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return ExamService.create_question_in_exam(db, exam_id, question_in, current_user)

@router.post("/{exam_id}/questions/bulk", response_model=dict)
def add_questions_to_exam(
    exam_id: UUID,
    question_in: QuestionBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    count = ExamService.add_questions_to_exam(db, exam_id, question_in, current_user)
    return {"message": f"Added {count} questions to exam"}
