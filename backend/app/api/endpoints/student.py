from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from fastapi_pagination import Page, paginate

from app.db.session import get_db
from app.models.user import User
from app.schemas.student import StudentExamResponse, SubmitExamRequest, SubmitExamResponse, StudentExamResultResponse, StudentExamListResponse
from app.api.deps import get_current_active_student
from app.services.student_service import StudentService

router = APIRouter()

@router.get("/exams", response_model=Page[StudentExamListResponse])
def get_available_exams(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_student)
):
    result = StudentService.get_available_exams(db=db, current_user_id=current_user.id, search=search)
    return paginate(result)

@router.get("/exams/{exam_id}/start", response_model=StudentExamResponse)
def start_exam(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_student)
):
    return StudentService.start_exam(db=db, current_user_id=current_user.id, exam_id=exam_id)

@router.post("/exams/{exam_id}/submit", response_model=SubmitExamResponse)
def submit_exam(
    exam_id: UUID,
    payload: SubmitExamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_student)
):
    return StudentService.submit_exam(db=db, current_user_id=current_user.id, exam_id=exam_id, payload=payload)

@router.get("/exams/{exam_id}/result", response_model=StudentExamResultResponse)
def get_exam_result(
    exam_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_student)
):
    return StudentService.get_exam_result(db=db, current_user_id=current_user.id, exam_id=exam_id)
