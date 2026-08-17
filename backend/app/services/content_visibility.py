from sqlalchemy import exists, or_, select

from app.models.exam import Exam
from app.models.flashcard import FlashcardDeck
from app.models.topic import Topic


class StudentContentVisibility:
    @staticmethod
    def topic_statement():
        published_owned_exam = exists(
            select(Exam.id).where(
                Exam.topic_id == Topic.id,
                Exam.creator_id == Topic.owner_id,
                Exam.is_published.is_(True),
            )
        )
        available_deck = exists(
            select(FlashcardDeck.id).where(FlashcardDeck.topic_id == Topic.id)
        )
        return select(Topic).where(
            Topic.owner_id.is_not(None),
            or_(published_owned_exam, available_deck),
        )

    @staticmethod
    def exam_statement():
        return select(Exam).where(
            Exam.creator_id.is_not(None),
            Exam.is_published.is_(True),
        )

    @staticmethod
    def deck_statement():
        return (
            select(FlashcardDeck)
            .join(Topic, FlashcardDeck.topic_id == Topic.id)
            .where(Topic.owner_id.is_not(None))
        )
