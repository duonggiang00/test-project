from typing import Optional
from uuid import UUID

from sqlalchemy import exists, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
from app.core.permissions import Permission, require_permission
from app.models.exam import Exam, Option, Question
from app.models.submission import Submission, SubmissionAnswer
from app.models.topic import Topic
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate
from app.schemas.question import QuestionBase, QuestionBulkCreate
from app.services.authorization_service import AuthorizationService


class ExamService:
    @staticmethod
    def _raise_if_exams_have_submissions(
        db: Session,
        exam_ids: set[UUID],
    ) -> None:
        if exam_ids and db.scalar(
            select(
                exists(
                    select(Submission.id).where(
                        Submission.exam_id.in_(exam_ids)
                    )
                )
            )
        ):
            raise AppException(
                status_code=409,
                error_code=(
                    "EXAM_QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS"
                ),
            )

    @staticmethod
    def _owned_exam_statement(current_user: User, permission: Permission):
        return AuthorizationService.scope_owned_statement(
            select(Exam),
            current_user,
            permission,
            Exam.creator_id,
        )

    @staticmethod
    def _require_topic_owner(
        db: Session,
        topic_id: UUID | None,
        owner_id: UUID | None,
    ) -> None:
        if topic_id is None:
            return
        owner_predicate = (
            Topic.owner_id.is_(None)
            if owner_id is None
            else Topic.owner_id == owner_id
        )
        topic = db.scalar(
            select(Topic.id).where(Topic.id == topic_id, owner_predicate)
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

    @staticmethod
    def get_exams_query(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        topic_id: Optional[UUID] = None,
    ):
        statement = ExamService._owned_exam_statement(
            current_user,
            Permission.READ_OWNED_CONTENT,
        )
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(Exam.title.ilike(f"%{safe_search}%"))
        if topic_id:
            statement = statement.where(Exam.topic_id == topic_id)
        return statement.order_by(Exam.created_at.desc(), Exam.id)

    @staticmethod
    def create_exam(
        db: Session,
        exam_in: ExamCreate,
        current_user: User,
    ) -> Exam:
        require_permission(current_user, Permission.CREATE_CONTENT)
        if exam_in.is_published:
            require_permission(current_user, Permission.PUBLISH_OWNED_CONTENT)
        ExamService._require_topic_owner(db, exam_in.topic_id, current_user.id)
        exam = Exam(
            title=exam_in.title,
            description=exam_in.description,
            duration_minutes=exam_in.duration_minutes,
            is_published=exam_in.is_published,
            topic_id=exam_in.topic_id,
            creator_id=current_user.id,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam

    @staticmethod
    def update_exam(
        db: Session,
        exam_id: UUID,
        exam_in: ExamUpdate,
        current_user: User,
    ) -> Exam:
        exam = db.scalar(
            ExamService._owned_exam_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            )
            .where(Exam.id == exam_id)
            .with_for_update()
        )
        if exam is None:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        ExamService._raise_if_exams_have_submissions(db, {exam.id})

        ExamService._require_topic_owner(db, exam_in.topic_id, exam.creator_id)
        if exam.is_published != exam_in.is_published:
            require_permission(current_user, Permission.PUBLISH_OWNED_CONTENT)

        exam.title = exam_in.title
        exam.description = exam_in.description
        exam.duration_minutes = exam_in.duration_minutes
        exam.is_published = exam_in.is_published
        exam.topic_id = exam_in.topic_id

        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="exam",
            entity_id=exam.id,
            owner_id=exam.creator_id,
            operation="update",
        )
        db.refresh(exam)
        return exam

    @staticmethod
    def delete_exam(
        db: Session,
        exam_id: UUID,
        current_user: User,
    ) -> None:
        exam = db.scalar(
            ExamService._owned_exam_statement(
                current_user,
                Permission.DELETE_OWNED_CONTENT,
            )
            .where(Exam.id == exam_id)
            .with_for_update()
        )
        if exam is None:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        if db.scalar(
            select(exists(select(Submission.id).where(Submission.exam_id == exam.id)))
        ):
            raise AppException(
                status_code=409,
                error_code="EXAM_DELETE_BLOCKED_BY_RETAINED_RECORDS",
            )

        db.delete(exam)
        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.DELETE_OWNED_CONTENT,
            entity_type="exam",
            entity_id=exam.id,
            owner_id=exam.creator_id,
            operation="delete",
        )

    @staticmethod
    def get_exam(
        db: Session,
        exam_id: UUID,
        current_user: User,
    ) -> Exam:
        exam = db.scalar(
            ExamService._owned_exam_statement(
                current_user,
                Permission.READ_OWNED_CONTENT,
            )
            .options(
                selectinload(Exam.questions).selectinload(Question.options)
            )
            .where(Exam.id == exam_id)
        )
        if exam is None:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        return exam

    @staticmethod
    def create_question_in_exam(
        db: Session,
        exam_id: UUID,
        question_in: QuestionBase,
        current_user: User,
    ) -> Question:
        exam = db.scalar(
            ExamService._owned_exam_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            )
            .where(Exam.id == exam_id)
            .with_for_update()
        )
        if exam is None:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        if exam.creator_id is None:
            raise AppException(status_code=409, error_code="CONTENT_OWNER_REQUIRED")
        ExamService._raise_if_exams_have_submissions(db, {exam.id})
        ExamService._require_topic_owner(db, question_in.topic_id, exam.creator_id)

        question = Question(
            owner_id=exam.creator_id,
            exam_id=exam.id,
            content=question_in.content,
            points=question_in.points,
            question_type=question_in.question_type,
            difficulty=question_in.difficulty,
            topic_id=question_in.topic_id,
            metadata_json=question_in.metadata_json,
            is_ai_generated=False,
        )
        db.add(question)
        db.flush()
        for option_in in question_in.options:
            db.add(
                Option(
                    question_id=question.id,
                    content=option_in.content,
                    is_correct=option_in.is_correct,
                )
            )

        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="exam",
            entity_id=exam.id,
            owner_id=exam.creator_id,
            operation="create_child",
        )
        fetched_question = db.scalar(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == question.id)
        )
        if fetched_question is None:
            raise RuntimeError("Created question could not be reloaded")
        return fetched_question

    @staticmethod
    def add_questions_to_exam(
        db: Session,
        exam_id: UUID,
        question_in: QuestionBulkCreate,
        current_user: User,
    ) -> int:
        exam = db.scalar(
            ExamService._owned_exam_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            )
            .where(Exam.id == exam_id)
        )
        if exam is None:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        if exam.creator_id is None:
            raise AppException(status_code=409, error_code="CONTENT_OWNER_REQUIRED")

        requested_ids = set(question_in.question_ids)
        same_owner_question = or_(
            Question.owner_id == exam.creator_id,
            (
                Question.owner_id.is_(None)
                & Question.exam.has(Exam.creator_id == exam.creator_id)
            ),
        )
        matched_questions = db.execute(
            select(Question.id, Question.exam_id)
            .where(
                Question.id.in_(requested_ids),
                same_owner_question,
            )
            .with_for_update()
        ).all()
        matched_ids = {row.id for row in matched_questions}
        if matched_ids != requested_ids:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")

        affected_exam_ids = {
            row.exam_id for row in matched_questions if row.exam_id is not None
        }
        affected_exam_ids.add(exam.id)
        locked_exam_ids = set(
            db.scalars(
                select(Exam.id)
                .where(Exam.id.in_(affected_exam_ids))
                .order_by(Exam.id)
                .with_for_update()
            ).all()
        )
        if exam.id not in locked_exam_ids:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        ExamService._raise_if_exams_have_submissions(db, affected_exam_ids)
        if db.scalar(
            select(
                exists(
                    select(SubmissionAnswer.id).where(
                        SubmissionAnswer.question_id.in_(requested_ids)
                    )
                )
            )
        ):
            raise AppException(
                status_code=409,
                error_code=(
                    "EXAM_QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS"
                ),
            )

        db.execute(
            update(Question)
            .where(
                Question.id.in_(requested_ids),
                same_owner_question,
            )
            .values(exam_id=exam.id, owner_id=exam.creator_id)
        )
        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="exam",
            entity_id=exam.id,
            owner_id=exam.creator_id,
            operation="bulk_assign",
        )
        return len(requested_ids)
