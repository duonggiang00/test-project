from typing import Optional
from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.permissions import (
    Permission,
    evaluate_owner_scope,
    require_permission,
)
from app.db.soft_delete import is_restorable, soft_delete
from app.models.exam import Exam, Question
from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.models.material import StudyMaterial
from app.models.submission import Submission
from app.models.topic import Topic
from app.models.topic_brief import TopicBrief
from app.models.user import User
from app.schemas.topic import TopicCreate, TopicUpdate
from app.services.authorization_service import AuthorizationService
from app.services.content_visibility import StudentContentVisibility


class TopicService:
    @staticmethod
    def _visible_topic_statement(current_user: User):
        statement = select(Topic)
        owner_scope = evaluate_owner_scope(
            current_user,
            Permission.READ_OWNED_CONTENT,
        )
        if owner_scope.allowed:
            return AuthorizationService.scope_owned_statement(
                statement,
                current_user,
                Permission.READ_OWNED_CONTENT,
                Topic.owner_id,
            )

        require_permission(current_user, Permission.READ_ASSIGNED_CONTENT)
        return StudentContentVisibility.topic_statement()

    @staticmethod
    def _owned_topic_statement(
        current_user: User,
        permission: Permission,
    ):
        return AuthorizationService.scope_owned_statement(
            select(Topic),
            current_user,
            permission,
            Topic.owner_id,
        )

    @staticmethod
    def _require_same_owner_parent(
        db: Session,
        parent_id: UUID | None,
        owner_id: UUID | None,
        *,
        current_topic_id: UUID | None = None,
    ) -> None:
        if parent_id is None:
            return
        if parent_id == current_topic_id:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
        owner_predicate = (
            Topic.owner_id.is_(None)
            if owner_id is None
            else Topic.owner_id == owner_id
        )
        parent = db.scalar(
            select(Topic.id).where(Topic.id == parent_id, owner_predicate)
        )
        if parent is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

    @staticmethod
    def get_topics_query(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
    ):
        statement = TopicService._visible_topic_statement(current_user)
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            statement = statement.where(Topic.name.ilike(f"%{safe_search}%"))
        return statement.order_by(Topic.created_at.desc(), Topic.id)

    @staticmethod
    def create_topic(
        db: Session,
        topic_in: TopicCreate,
        current_user: User,
    ) -> Topic:
        require_permission(current_user, Permission.CREATE_CONTENT)
        TopicService._require_same_owner_parent(
            db,
            topic_in.parent_id,
            current_user.id,
        )
        topic = Topic(
            owner_id=current_user.id,
            name=topic_in.name,
            description=topic_in.description,
            parent_id=topic_in.parent_id,
            brief_content=topic_in.brief_content,
            brief_ai_generated=topic_in.brief_ai_generated,
        )
        db.add(topic)
        db.flush()
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            entity_type="topic",
            entity_id=topic.id,
            owner_id=topic.owner_id,
            action="topic.create",
        )
        db.refresh(topic)
        return topic

    @staticmethod
    def get_topic(
        db: Session,
        topic_id: UUID,
        current_user: User,
    ) -> Topic:
        topic = db.scalar(
            TopicService._visible_topic_statement(current_user).where(
                Topic.id == topic_id
            )
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
        return topic

    @staticmethod
    def update_topic(
        db: Session,
        topic_id: UUID,
        topic_in: TopicUpdate,
        current_user: User,
    ) -> Topic:
        topic = db.scalar(
            TopicService._owned_topic_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            ).where(Topic.id == topic_id)
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

        if "parent_id" in topic_in.model_fields_set:
            TopicService._require_same_owner_parent(
                db,
                topic_in.parent_id,
                topic.owner_id,
                current_topic_id=topic.id,
            )
            topic.parent_id = topic_in.parent_id
        if topic_in.name is not None:
            topic.name = topic_in.name
        if topic_in.description is not None:
            topic.description = topic_in.description

        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="topic",
            entity_id=topic.id,
            owner_id=topic.owner_id,
            operation="update",
            action="topic.update",
        )
        db.refresh(topic)
        return topic

    @staticmethod
    def delete_topic(
        db: Session,
        topic_id: UUID,
        current_user: User,
    ) -> None:
        topic = db.scalar(
            TopicService._owned_topic_statement(
                current_user,
                Permission.DELETE_OWNED_CONTENT,
            )
            .where(Topic.id == topic_id)
            .with_for_update()
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

        # Blocking on any linked Exam here (regardless of whether that exam
        # has submissions) transitively protects submission/grade
        # visibility: a Topic can never be soft-deleted while an Exam still
        # references it, and that Exam itself cannot be soft-deleted while
        # it has live Submissions (see exam_service.delete_exam). This is
        # why AnalyticsService/HistoryService/StudentService.get_exam_result
        # can safely read through the default soft-delete-filtered Session
        # (see app/db/soft_delete.py) without a Topic ever vanishing out
        # from under a retained submission. If this guard is ever relaxed,
        # re-audit those three read paths for silently vanishing data.
        linked_record_exists = db.scalar(
            select(
                or_(
                    exists(select(Topic.id).where(Topic.parent_id == topic.id)),
                    exists(select(Exam.id).where(Exam.topic_id == topic.id)),
                    exists(select(Question.id).where(Question.topic_id == topic.id)),
                    exists(
                        select(StudyMaterial.id).where(
                            StudyMaterial.topic_id == topic.id
                        )
                    ),
                    exists(
                        select(FlashcardDeck.id).where(
                            FlashcardDeck.topic_id == topic.id
                        )
                    ),
                    exists(
                        select(TopicBrief.id).where(
                            TopicBrief.topic_id == topic.id
                        )
                    ),
                )
            )
        )
        if linked_record_exists:
            raise AppException(
                status_code=409,
                error_code="TOPIC_DELETE_BLOCKED_BY_LINKED_RECORDS",
            )

        soft_delete(topic, current_user.id)
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            permission=Permission.DELETE_OWNED_CONTENT,
            entity_type="topic",
            entity_id=topic.id,
            owner_id=topic.owner_id,
            operation="delete",
            action="topic.delete",
        )

    @staticmethod
    def restore_topic(
        db: Session,
        topic_id: UUID,
        current_user: User,
    ) -> Topic:
        topic = db.scalar(
            TopicService._owned_topic_statement(
                current_user,
                Permission.RESTORE_OWNED_CONTENT,
            )
            .where(Topic.id == topic_id, Topic.deleted_at.is_not(None))
            .execution_options(include_deleted=True)
            .with_for_update()
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

        if not is_restorable(topic.deleted_at):
            raise AppException(
                status_code=409,
                error_code="TOPIC_RESTORE_WINDOW_EXPIRED",
            )

        deleted_at_before = topic.deleted_at
        topic.deleted_at = None
        topic.deleted_by_id = None

        AuthorizationService.commit_restore(
            db,
            actor=current_user,
            permission=Permission.RESTORE_OWNED_CONTENT,
            entity_type="topic",
            entity_id=topic.id,
            owner_id=topic.owner_id,
            deleted_at_before=deleted_at_before,
        )
        db.refresh(topic)
        return topic

    @staticmethod
    def get_topic_progress(
        db: Session,
        topic_id: UUID,
        current_user: User,
    ) -> float:
        topic = db.scalar(
            TopicService._visible_topic_statement(current_user)
            .with_only_columns(Topic.id)
            .where(Topic.id == topic_id)
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

        total_exams = db.scalar(
            select(func.count(Exam.id)).where(
                Exam.topic_id == topic_id,
                Exam.is_published.is_(True),
            )
        ) or 0
        completed_exams = db.scalar(
            select(func.count(func.distinct(Exam.id)))
            .join(Submission, Submission.exam_id == Exam.id)
            .where(
                Exam.topic_id == topic_id,
                Exam.is_published.is_(True),
                Submission.student_id == current_user.id,
                Submission.status == "submitted",
            )
        ) or 0
        total_decks = db.scalar(
            select(func.count(FlashcardDeck.id)).where(
                FlashcardDeck.topic_id == topic_id
            )
        ) or 0
        completed_decks = db.scalar(
            select(func.count(func.distinct(FlashcardDeck.id)))
            .join(Flashcard, Flashcard.deck_id == FlashcardDeck.id)
            .join(
                FlashcardProgress,
                FlashcardProgress.flashcard_id == Flashcard.id,
            )
            .where(
                FlashcardDeck.topic_id == topic_id,
                FlashcardProgress.student_id == current_user.id,
            )
        ) or 0

        total_resources = total_exams + total_decks
        if total_resources == 0:
            return 0.0
        return round(((completed_exams + completed_decks) / total_resources) * 100, 1)
