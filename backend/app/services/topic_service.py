from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicUpdate
from app.core.exceptions import AppException
from app.models.user import User
from app.models.exam import Exam
from app.models.submission import Submission
from app.models.flashcard import FlashcardDeck, Flashcard, FlashcardProgress
class TopicService:
    @staticmethod
    def get_topics_query(db: Session, search: Optional[str] = None):
        query = db.query(Topic)
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            query = query.filter(Topic.name.ilike(f"%{safe_search}%"))
        return query

    @staticmethod
    def create_topic(db: Session, topic_in: TopicCreate, current_user: User) -> Topic:
        topic = Topic(
            name=topic_in.name,
            description=topic_in.description,
            parent_id=topic_in.parent_id
        )
        db.add(topic)
        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def get_topic(db: Session, topic_id: UUID) -> Topic:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
        return topic

    @staticmethod
    def update_topic(db: Session, topic_id: UUID, topic_in: TopicUpdate, current_user: User) -> Topic:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
            
        if topic_in.name is not None:
            topic.name = topic_in.name
        if topic_in.description is not None:
            topic.description = topic_in.description
        if topic_in.parent_id is not None:
            topic.parent_id = topic_in.parent_id
            
        db.commit()
        db.refresh(topic)
        return topic

    @staticmethod
    def delete_topic(db: Session, topic_id: UUID, current_user: User):
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")
            
        db.delete(topic)
        db.commit()

    @staticmethod
    def get_topic_progress(db: Session, topic_id: UUID, user_id: UUID) -> float:
        # 1. Total Exams & Completed Exams
        total_exams = db.query(Exam).filter(Exam.topic_id == topic_id).count()
        completed_exams = db.query(Exam).join(Submission).filter(
            Exam.topic_id == topic_id,
            Submission.student_id == user_id,
            Submission.status == "completed"
        ).count()

        # 2. Total Decks & Completed Decks
        total_decks = db.query(FlashcardDeck).filter(FlashcardDeck.topic_id == topic_id).count()
        # A deck is considered "studied" if the user has at least one FlashcardProgress for a card in that deck
        completed_decks = db.query(FlashcardDeck).join(Flashcard).join(FlashcardProgress).filter(
            FlashcardDeck.topic_id == topic_id,
            FlashcardProgress.student_id == user_id
        ).distinct().count()

        total_resources = total_exams + total_decks
        if total_resources == 0:
            return 0.0

        completed_resources = completed_exams + completed_decks
        return round((completed_resources / total_resources) * 100, 1)
