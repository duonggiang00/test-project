from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import AppException
from app.core.permissions import Permission
from app.models.exam import Exam, Question
from app.models.submission import Submission
from app.models.user import User
from app.schemas.history import SubmissionAnswerDetail, SubmissionDetailResponse
from app.services.authorization_service import AuthorizationService


class HistoryService:
    @staticmethod
    def _owned_submission_statement(current_user: User):
        statement = select(Submission).join(
            Exam,
            Submission.exam_id == Exam.id,
        )
        return AuthorizationService.scope_owned_statement(
            statement,
            current_user,
            Permission.READ_OWNED_EXAM_SUBMISSIONS,
            Exam.creator_id,
        )

    @staticmethod
    def get_submission_history(
        db: Session,
        current_user: User,
        student_id: Optional[UUID] = None,
        exam_id: Optional[UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ):
        statement = HistoryService._owned_submission_statement(
            current_user
        ).options(
            joinedload(Submission.exam),
            joinedload(Submission.student),
        )
        if student_id:
            statement = statement.where(Submission.student_id == student_id)
        if exam_id:
            statement = statement.where(Submission.exam_id == exam_id)
        if status:
            statement = statement.where(Submission.status == status)
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            statement = statement.join(
                User,
                Submission.student_id == User.id,
            ).where(
                User.full_name.ilike(f"%{safe_search}%")
                | User.email.ilike(f"%{safe_search}%")
            )
        return statement.order_by(Submission.start_time.desc(), Submission.id)

    @staticmethod
    def get_submission_detail(
        db: Session,
        submission_id: UUID,
        current_user: User,
    ) -> SubmissionDetailResponse:
        submission = db.scalar(
            HistoryService._owned_submission_statement(current_user)
            .options(
                joinedload(Submission.exam),
                joinedload(Submission.student),
                selectinload(Submission.answers),
            )
            .where(Submission.id == submission_id)
        )
        if submission is None:
            raise AppException(status_code=404, error_code="SUBMISSION_NOT_FOUND")

        questions = db.scalars(
            select(Question).where(Question.exam_id == submission.exam_id)
        ).all()
        question_content = {question.id: question.content for question in questions}
        answers = [
            SubmissionAnswerDetail(
                question_id=answer.question_id,
                question_content=question_content.get(
                    answer.question_id,
                    "Question unavailable",
                ),
                answer_data=answer.answer_data,
                is_correct=answer.is_correct,
                points_awarded=answer.points_awarded,
            )
            for answer in submission.answers
        ]
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
            answers=answers,
        )
