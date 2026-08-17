from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.session import get_db
from app.models.user import User
from app.schemas.history import SubmissionHistoryItem, SubmissionDetailResponse
from app.api.deps import get_current_active_teacher
from app.services.history_service import HistoryService

router = APIRouter()

@router.get("/submissions", response_model=Page[SubmissionHistoryItem])
def get_submission_history(
    student_id: Optional[UUID] = None,
    exam_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Get paginated submission history for teachers/admins with eager loading.
    """
    query = HistoryService.get_submission_history(
        db=db,
        current_user=current_user,
        student_id=student_id,
        exam_id=exam_id,
        status=status,
        search=search
    )
    return paginate(db, query)

@router.get("/submissions/{submission_id}", response_model=SubmissionDetailResponse)
def get_submission_detail(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Get full submission detail with questions and student answers.
    """
    return HistoryService.get_submission_detail(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )
