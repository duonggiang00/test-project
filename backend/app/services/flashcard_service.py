from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
from app.core.permissions import (
    Permission,
    evaluate_owner_scope,
    require_permission,
)
from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from app.services.authorization_service import AuthorizationService
from app.services.content_visibility import StudentContentVisibility


@dataclass(frozen=True)
class AuthorizedTopicKit:
    owner_id: UUID
    actor_id: UUID


class FlashcardService:
    @staticmethod
    def _owned_topic_statement(current_user: User, permission: Permission):
        return AuthorizationService.scope_owned_statement(
            select(Topic),
            current_user,
            permission,
            Topic.owner_id,
        )

    @staticmethod
    def _owned_deck_statement(current_user: User, permission: Permission):
        statement = select(FlashcardDeck).join(
            Topic,
            FlashcardDeck.topic_id == Topic.id,
        )
        return AuthorizationService.scope_owned_statement(
            statement,
            current_user,
            permission,
            Topic.owner_id,
        )

    @staticmethod
    def _readable_deck_statement(current_user: User):
        owner_scope = evaluate_owner_scope(
            current_user,
            Permission.READ_OWNED_CONTENT,
        )
        if owner_scope.allowed:
            return FlashcardService._owned_deck_statement(
                current_user,
                Permission.READ_OWNED_CONTENT,
            )
        require_permission(current_user, Permission.READ_ASSIGNED_CONTENT)
        # Decks have no publication/assignment state in the current schema.
        # Authenticated students retain the existing learning-library behavior.
        return StudentContentVisibility.deck_statement()

    @staticmethod
    def authorize_topic_kit(
        db: Session,
        material_id: UUID,
        topic_id: UUID,
        current_user: User,
    ) -> AuthorizedTopicKit:
        require_permission(current_user, Permission.CREATE_CONTENT)
        material = db.scalar(
            AuthorizationService.scope_owned_statement(
                select(StudyMaterial),
                current_user,
                Permission.READ_OWNED_CONTENT,
                StudyMaterial.uploader_id,
            ).where(StudyMaterial.id == material_id)
        )
        if material is None:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND")
        topic = db.scalar(
            FlashcardService._owned_topic_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            ).where(Topic.id == topic_id)
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
        if (
            material.uploader_id is None
            or topic.owner_id is None
            or material.uploader_id != topic.owner_id
        ):
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

        return AuthorizedTopicKit(
            owner_id=topic.owner_id,
            actor_id=current_user.id,
        )

    @staticmethod
    def update_topic_brief(
        db: Session,
        topic_id: UUID,
        brief_content: str,
        brief_ai_generated: bool,
        current_user: User,
    ) -> Topic:
        topic = db.scalar(
            FlashcardService._owned_topic_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            ).where(Topic.id == topic_id)
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

        topic.brief_content = brief_content
        topic.brief_ai_generated = brief_ai_generated
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
        return topic

    @staticmethod
    def create_deck(
        db: Session,
        deck_data: dict,
        current_user: User,
    ) -> FlashcardDeck:
        require_permission(current_user, Permission.CREATE_CONTENT)
        topic_id = deck_data.get("topic_id")
        topic = db.scalar(
            FlashcardService._owned_topic_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            ).where(Topic.id == topic_id)
        )
        if topic is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
        if topic.owner_id is None:
            raise AppException(status_code=409, error_code="CONTENT_OWNER_REQUIRED")

        new_deck = FlashcardDeck(**deck_data)
        db.add(new_deck)
        db.flush()
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="flashcard_deck",
            entity_id=new_deck.id,
            owner_id=topic.owner_id,
            override_entity_type="topic",
            override_entity_id=topic.id,
            operation="create_child",
            action="flashcard_deck.create",
        )
        db.refresh(new_deck)
        return new_deck

    @staticmethod
    def get_topic_decks(
        db: Session,
        topic_id: UUID,
        current_user: User,
    ):
        statement = FlashcardService._readable_deck_statement(
            current_user
        ).where(FlashcardDeck.topic_id == topic_id)
        decks = db.scalars(statement.order_by(FlashcardDeck.created_at, FlashcardDeck.id)).all()
        if not decks:
            topic_statement = select(Topic.id).where(Topic.id == topic_id)
            owner_scope = evaluate_owner_scope(
                current_user,
                Permission.READ_OWNED_CONTENT,
            )
            if owner_scope.allowed:
                topic_statement = AuthorizationService.scope_owned_statement(
                    topic_statement,
                    current_user,
                    Permission.READ_OWNED_CONTENT,
                    Topic.owner_id,
                )
            else:
                require_permission(
                    current_user,
                    Permission.READ_ASSIGNED_CONTENT,
                )
                topic_statement = (
                    StudentContentVisibility.topic_statement()
                    .with_only_columns(Topic.id)
                    .where(Topic.id == topic_id)
                )
            if db.scalar(topic_statement) is None:
                raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
        return decks

    @staticmethod
    def get_deck(
        db: Session,
        deck_id: UUID,
        current_user: User,
    ) -> FlashcardDeck:
        deck = db.scalar(
            FlashcardService._readable_deck_statement(current_user)
            .options(selectinload(FlashcardDeck.flashcards))
            .where(FlashcardDeck.id == deck_id)
        )
        if deck is None:
            raise AppException(status_code=404, error_code="DECK_NOT_FOUND")
        return deck

    @staticmethod
    def create_card(
        db: Session,
        deck_id: UUID,
        card_data: dict,
        current_user: User,
    ) -> Flashcard:
        if card_data.get("deck_id") != deck_id:
            raise AppException(status_code=400, error_code="DECK_MISMATCH")
        deck = db.scalar(
            FlashcardService._owned_deck_statement(
                current_user,
                Permission.UPDATE_OWNED_CONTENT,
            )
            .options(selectinload(FlashcardDeck.topic))
            .where(FlashcardDeck.id == deck_id)
        )
        if deck is None:
            raise AppException(status_code=404, error_code="DECK_NOT_FOUND")

        new_card = Flashcard(**card_data)
        db.add(new_card)
        db.flush()
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="flashcard",
            entity_id=new_card.id,
            owner_id=deck.topic.owner_id,
            override_entity_type="flashcard_deck",
            override_entity_id=deck.id,
            operation="create_child",
            action="flashcard.create",
        )
        db.refresh(new_card)
        return new_card

    @staticmethod
    def get_study_cards(
        db: Session,
        deck_id: UUID,
        current_user: User,
    ):
        deck = db.scalar(
            FlashcardService._readable_deck_statement(current_user).where(
                FlashcardDeck.id == deck_id
            )
        )
        if deck is None:
            raise AppException(status_code=404, error_code="DECK_NOT_FOUND")
        cards = db.scalars(
            select(Flashcard)
            .where(Flashcard.deck_id == deck.id)
            .order_by(Flashcard.order_index, Flashcard.id)
        ).all()
        if not cards:
            return []

        card_ids = [card.id for card in cards]
        progresses = db.scalars(
            select(FlashcardProgress).where(
                FlashcardProgress.student_id == current_user.id,
                FlashcardProgress.flashcard_id.in_(card_ids),
            )
        ).all()
        progress_map = {progress.flashcard_id: progress for progress in progresses}
        now = datetime.now(timezone.utc)
        return [
            card
            for card in cards
            if (progress := progress_map.get(card.id)) is None
            or progress.next_review_at <= now
        ]

    @staticmethod
    def review_card(
        db: Session,
        card_id: UUID,
        current_user: User,
        rating_str: str,
    ):
        rating = rating_str.upper()
        if rating not in {"EASY", "GOOD", "HARD", "AGAIN"}:
            raise AppException(status_code=400, error_code="INVALID_RATING")

        card = db.scalar(
            select(Flashcard)
            .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
            .join(Topic, FlashcardDeck.topic_id == Topic.id)
            .where(
                Flashcard.id == card_id,
                Topic.owner_id.is_not(None),
            )
            .with_for_update(read=True, of=Flashcard)
        )
        if card is None:
            raise AppException(status_code=404, error_code="FLASHCARD_NOT_FOUND")
        require_permission(current_user, Permission.READ_ASSIGNED_CONTENT)

        progress = db.scalar(
            select(FlashcardProgress).where(
                FlashcardProgress.student_id == current_user.id,
                FlashcardProgress.flashcard_id == card.id,
            )
        )
        if progress is None:
            progress = FlashcardProgress(
                student_id=current_user.id,
                flashcard_id=card.id,
                box_level=0,
            )
            db.add(progress)

        if rating == "AGAIN":
            progress.box_level = max(0, progress.box_level - 2)
        elif rating == "HARD":
            progress.box_level = max(1, progress.box_level - 1)
        elif rating == "GOOD":
            progress.box_level = min(5, progress.box_level + 1)
        else:
            progress.box_level = min(5, progress.box_level + 2)

        intervals = {
            0: timedelta(minutes=10),
            1: timedelta(days=1),
            2: timedelta(days=3),
            3: timedelta(days=7),
            4: timedelta(days=14),
            5: timedelta(days=30),
        }
        now = datetime.now(timezone.utc)
        progress.last_reviewed_at = now
        progress.next_review_at = now + intervals.get(
            progress.box_level,
            timedelta(days=30),
        )
        db.commit()
        return {
            "status": "success",
            "box_level": progress.box_level,
            "next_review_at": progress.next_review_at,
        }
