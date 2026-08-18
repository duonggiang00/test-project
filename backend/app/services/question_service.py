from typing import Optional
from uuid import UUID

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
from app.core.permissions import Permission, require_owner_scope, require_permission
from app.db.soft_delete import is_restorable, soft_delete
from app.models.exam import Exam, Option, Question
from app.models.submission import Submission, SubmissionAnswer
from app.models.topic import Topic
from app.models.user import User
from app.schemas.question import QuestionBase, QuestionUpdate
from app.services.authorization_service import AuthorizationService


class QuestionService:
    @staticmethod
    def _raise_if_question_is_retained(
        db: Session,
        question: Question,
    ) -> None:
        if question.exam_id is not None:
            locked_exam_id = db.scalar(
                select(Exam.id)
                .where(Exam.id == question.exam_id)
                .with_for_update()
            )
            if locked_exam_id is None:
                raise AppException(
                    status_code=409,
                    error_code="QUESTION_PARENT_EXAM_REQUIRED",
                )
        if db.scalar(
            select(
                or_(
                    exists(
                        select(Submission.id).where(
                            Submission.exam_id == question.exam_id
                        )
                    )
                    if question.exam_id is not None
                    else False,
                    exists(
                        select(SubmissionAnswer.id).where(
                            SubmissionAnswer.question_id == question.id
                        )
                    ),
                )
            )
        ):
            raise AppException(
                status_code=409,
                error_code=(
                    "QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS"
                ),
            )

    @staticmethod
    def _owned_question_statement(
        current_user: User,
        permission: Permission,
    ):
        scope = require_owner_scope(current_user, permission)
        statement = select(Question)
        if scope.scoped_owner_id is None:
            return statement
        return statement.where(
            or_(
                Question.owner_id == scope.scoped_owner_id,
                (
                    Question.owner_id.is_(None)
                    & Question.exam.has(
                        Exam.creator_id == scope.scoped_owner_id
                    )
                ),
            )
        )

    @staticmethod
    def _effective_owner_id(question: Question) -> UUID | None:
        if question.owner_id is not None:
            return question.owner_id
        if question.exam is not None:
            return question.exam.creator_id
        return None

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
        if db.scalar(
            select(Topic.id).where(Topic.id == topic_id, owner_predicate)
        ) is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

    @staticmethod
    def get_questions_query(
        db: Session,
        current_user: User,
        topic_id: Optional[UUID] = None,
        difficulty: Optional[str] = None,
        search: Optional[str] = None,
    ):
        statement = QuestionService._owned_question_statement(
            current_user,
            Permission.READ_OWNED_CONTENT,
        ).options(selectinload(Question.options))
        if topic_id:
            statement = statement.where(Question.topic_id == topic_id)
        if difficulty:
            statement = statement.where(Question.difficulty == difficulty.upper())
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(
                Question.content.ilike(f"%{safe_search}%")
            )
        return statement.order_by(Question.created_at.desc(), Question.id)

    @staticmethod
    def create_question(
        db: Session,
        question_in: QuestionBase,
        current_user: User,
    ) -> Question:
        require_permission(current_user, Permission.CREATE_CONTENT)
        QuestionService._require_topic_owner(
            db,
            question_in.topic_id,
            current_user.id,
        )
        question = Question(
            owner_id=current_user.id,
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
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            entity_type="question",
            entity_id=question.id,
            owner_id=current_user.id,
            action="question.create",
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
    def get_question(
        db: Session,
        question_id: UUID,
        current_user: User,
    ) -> Question:
        question = db.scalar(
            QuestionService._owned_question_statement(
                current_user,
                Permission.READ_OWNED_CONTENT,
            )
            .options(
                selectinload(Question.options),
                selectinload(Question.exam),
            )
            .where(Question.id == question_id)
        )
        if question is None:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")
        return question

    @staticmethod
    def update_question(
        db: Session,
        question_id: UUID,
        question_in: QuestionUpdate,
        current_user: User,
    ) -> Question:
        question = db.scalar(
            QuestionService._owned_question_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            )
            .options(
                selectinload(Question.options),
                selectinload(Question.exam),
            )
            .where(Question.id == question_id)
            .with_for_update()
        )
        if question is None:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")

        QuestionService._raise_if_question_is_retained(db, question)

        owner_id = QuestionService._effective_owner_id(question)
        if "topic_id" in question_in.model_fields_set:
            QuestionService._require_topic_owner(
                db,
                question_in.topic_id,
                owner_id,
            )
            question.topic_id = question_in.topic_id
        if question_in.content is not None:
            question.content = question_in.content
        if question_in.points is not None:
            question.points = question_in.points
        if question_in.question_type is not None:
            question.question_type = question_in.question_type
        if question_in.difficulty is not None:
            question.difficulty = question_in.difficulty
        if question_in.metadata_json is not None:
            question.metadata_json = question_in.metadata_json
        if owner_id is not None:
            question.owner_id = owner_id

        if question_in.options is not None:
            db.execute(delete(Option).where(Option.question_id == question.id))
            for option_in in question_in.options:
                db.add(
                    Option(
                        question_id=question.id,
                        content=option_in.content,
                        is_correct=option_in.is_correct,
                    )
                )

        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="question",
            entity_id=question.id,
            owner_id=owner_id,
            operation="update",
            action="question.update",
        )
        fetched_question = db.scalar(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == question.id)
        )
        if fetched_question is None:
            raise RuntimeError("Updated question could not be reloaded")
        return fetched_question

    @staticmethod
    def delete_question(
        db: Session,
        question_id: UUID,
        current_user: User,
    ) -> None:
        question = db.scalar(
            QuestionService._owned_question_statement(
                current_user,
                Permission.DELETE_OWNED_CONTENT,
            )
            .options(selectinload(Question.exam))
            .where(Question.id == question_id)
            .with_for_update()
        )
        if question is None:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")
        QuestionService._raise_if_question_is_retained(db, question)

        owner_id = QuestionService._effective_owner_id(question)
        soft_delete(question, current_user.id)
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            permission=Permission.DELETE_OWNED_CONTENT,
            entity_type="question",
            entity_id=question.id,
            owner_id=owner_id,
            operation="delete",
            action="question.delete",
        )

    @staticmethod
    def restore_question(
        db: Session,
        question_id: UUID,
        current_user: User,
    ) -> Question:
        question = db.scalar(
            QuestionService._owned_question_statement(
                current_user,
                Permission.RESTORE_OWNED_CONTENT,
            )
            .options(
                selectinload(Question.options),
                selectinload(Question.exam),
            )
            .where(Question.id == question_id, Question.deleted_at.is_not(None))
            .execution_options(include_deleted=True)
            .with_for_update()
        )
        if question is None:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")

        if not is_restorable(question.deleted_at):
            raise AppException(
                status_code=409,
                error_code="QUESTION_RESTORE_WINDOW_EXPIRED",
            )

        owner_id = QuestionService._effective_owner_id(question)
        deleted_at_before = question.deleted_at
        question.deleted_at = None
        question.deleted_by_id = None

        AuthorizationService.commit_restore(
            db,
            actor=current_user,
            permission=Permission.RESTORE_OWNED_CONTENT,
            entity_type="question",
            entity_id=question.id,
            owner_id=owner_id,
            deleted_at_before=deleted_at_before,
        )
        fetched_question = db.scalar(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == question.id)
        )
        if fetched_question is None:
            raise RuntimeError("Restored question could not be reloaded")
        return fetched_question
