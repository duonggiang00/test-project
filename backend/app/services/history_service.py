from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import AppException
from app.core.permissions import Permission
from app.models.exam import Exam, Question
from app.models.submission import Submission
from app.models.user import User
from app.schemas.history import (
    GradeOverrideRequest,
    SubmissionAnswerDetail,
    SubmissionDetailResponse,
)
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
        question_by_id = {question.id: question for question in questions}
        answers = [
            SubmissionAnswerDetail(
                question_id=answer.question_id,
                question_content=(
                    question.content
                    if (question := question_by_id.get(answer.question_id))
                    else "Question unavailable"
                ),
                answer_data=answer.answer_data,
                is_correct=answer.is_correct,
                points_awarded=answer.points_awarded,
                max_points=question.points if question else None,
                override_reason=answer.override_reason,
                overridden_at=answer.overridden_at,
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

    @staticmethod
    def override_answer_grade(
        db: Session,
        submission_id: UUID,
        question_id: UUID,
        request: GradeOverrideRequest,
        current_user: User,
    ) -> SubmissionDetailResponse:
        """Correct one answer's score, recomputing the submission total.

        Three things are deliberately not accepted from the caller:

        - `total_score`, which is recomputed as the sum of the answers, so a
          total can never disagree with its parts.
        - `is_correct`, which is derived with the same rule the automatic
          grader uses (`student_service.submit_exam`), so the two fields
          cannot drift apart.
        - `Submission.status`, which is left alone entirely. `AnalyticsService`
          aggregates only `status == "submitted"` in three separate live
          queries; moving a corrected submission to some other status would
          silently drop it out of every report while it still appeared in
          history.

        The submission row is locked with `FOR UPDATE OF submissions` so two
        reviewers correcting different answers of the same submission
        serialize instead of racing to write `total_score`. The lock is
        narrowed with `of=` because the owner-scoping statement joins `Exam`,
        and a bare `FOR UPDATE` would also lock the exam row, blocking
        unrelated edits to it.
        """
        submission = db.scalar(
            HistoryService._owned_submission_statement(current_user)
            .options(
                joinedload(Submission.exam),
                joinedload(Submission.student),
                selectinload(Submission.answers),
            )
            .where(Submission.id == submission_id)
            .with_for_update(of=Submission)
        )
        if submission is None:
            raise AppException(status_code=404, error_code="SUBMISSION_NOT_FOUND")

        answer = next(
            (
                item
                for item in submission.answers
                if item.question_id == question_id
            ),
            None,
        )
        if answer is None:
            raise AppException(
                status_code=404, error_code="SUBMISSION_ANSWER_NOT_FOUND"
            )

        question = db.scalar(
            select(Question).where(Question.id == question_id)
        )
        if question is None:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")

        max_points = float(question.points)
        if request.points_awarded > max_points:
            raise AppException(
                status_code=422,
                error_code="GRADE_OVERRIDE_EXCEEDS_QUESTION_POINTS",
            )

        previous_points = float(answer.points_awarded or 0.0)
        previous_total = float(submission.total_score or 0.0)

        answer.points_awarded = request.points_awarded
        answer.is_correct = request.points_awarded == max_points
        answer.override_reason = request.reason
        answer.overridden_at = datetime.now(timezone.utc)
        answer.overridden_by_id = current_user.id

        submission.total_score = sum(
            float(item.points_awarded or 0.0) for item in submission.answers
        )

        # `owner_id` is the exam's creator, not the student. The grading
        # permission is evaluated against exam ownership
        # (`_owned_submission_statement` scopes on `Exam.creator_id`), so
        # passing the student here would deny every teacher. This
        # deliberately differs from `submission.graded`, whose owner is the
        # student who submitted; see the note on the audit policy entry.
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            action="submission.grade_override",
            entity_type="submission",
            entity_id=submission.id,
            owner_id=submission.exam.creator_id if submission.exam else None,
            permission=Permission.GRADE_OWNED_EXAM_SUBMISSION,
            override_entity_type="exam",
            override_entity_id=submission.exam_id,
            operation="update",
            changes={
                "points_awarded": {
                    "before": previous_points,
                    "after": float(request.points_awarded),
                },
                "total_score": {
                    "before": previous_total,
                    "after": float(submission.total_score),
                },
            },
            metadata={
                "question_id": str(question_id),
                "max_score": max_points,
            },
        )

        return HistoryService.get_submission_detail(
            db, submission_id, current_user
        )
