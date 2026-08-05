from sqlalchemy.orm import Session, selectinload, joinedload
from typing import Optional
from uuid import UUID

from app.models.submission import Submission
from app.models.user import User
from app.models.exam import Question
from app.schemas.history import SubmissionAnswerDetail, SubmissionDetailResponse
from app.core.exceptions import AppException

class HistoryService:
    @staticmethod
    def get_submission_history(
        db: Session,
        student_id: Optional[UUID] = None,
        exam_id: Optional[UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None
    ):
        query = db.query(Submission).options(
            joinedload(Submission.exam),
            joinedload(Submission.student)
        )
        
        if student_id:
            query = query.filter(Submission.student_id == student_id)
        if exam_id:
            query = query.filter(Submission.exam_id == exam_id)
        if status:
            query = query.filter(Submission.status == status)
        if search:
            query = query.join(User, Submission.student_id == User.id).filter(
                (User.full_name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
            )
            
        return query

    @staticmethod
    def get_submission_detail(db: Session, submission_id: UUID) -> SubmissionDetailResponse:
        submission = db.query(Submission).options(
            joinedload(Submission.exam),
            joinedload(Submission.student),
            selectinload(Submission.answers)
        ).filter(Submission.id == submission_id).first()
        
        if not submission:
            raise AppException(status_code=404, error_code="SUBMISSION_NOT_FOUND")
            
        questions = db.query(Question).filter(Question.exam_id == submission.exam_id).all()
        q_map = {q.id: q.content for q in questions}
        
        answers_detail = []
        for ans in submission.answers:
            answers_detail.append(SubmissionAnswerDetail(
                question_id=ans.question_id,
                question_content=q_map.get(ans.question_id, "Question deleted"),
                answer_data=ans.answer_data,
                is_correct=ans.is_correct,
                points_awarded=ans.points_awarded
            ))
            
        return SubmissionDetailResponse(
            id=submission.id,
            exam_id=submission.exam_id,
            exam_title=submission.exam_title,
            student_id=submission.student_id,
            student_name=submission.student_name,
            student_email=submission.student_email,
            start_time=submission.start_time,
            end_time=submission.end_time,
            total_score=submission.total_score,
            status=submission.status,
            answers=answers_detail
        )
