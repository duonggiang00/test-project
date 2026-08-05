from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta
from typing import List

from app.models.flashcard import FlashcardDeck, Flashcard, FlashcardProgress
from app.models.topic import Topic
from app.core.exceptions import AppException

class FlashcardService:
    @staticmethod
    def update_topic_brief(db: Session, topic_id: UUID, brief_content: str, brief_ai_generated: bool):
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND", detail="Topic not found")
        
        topic.brief_content = brief_content
        topic.brief_ai_generated = brief_ai_generated
        db.commit()
        return topic

    @staticmethod
    def create_deck(db: Session, deck_data: dict):
        new_deck = FlashcardDeck(**deck_data)
        db.add(new_deck)
        db.commit()
        db.refresh(new_deck)
        return new_deck

    @staticmethod
    def get_topic_decks(db: Session, topic_id: UUID):
        return db.query(FlashcardDeck).filter(FlashcardDeck.topic_id == topic_id).all()

    @staticmethod
    def get_deck(db: Session, deck_id: UUID):
        deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()
        if not deck:
            raise AppException(status_code=404, error_code="DECK_NOT_FOUND", detail="Deck not found")
        return deck

    @staticmethod
    def create_card(db: Session, deck_id: UUID, card_data: dict):
        if card_data.get("deck_id") != deck_id:
            raise AppException(status_code=400, error_code="DECK_MISMATCH", detail="Deck ID mismatch")
        new_card = Flashcard(**card_data)
        db.add(new_card)
        db.commit()
        db.refresh(new_card)
        return new_card

    @staticmethod
    def get_study_cards(db: Session, deck_id: UUID, student_id: UUID):
        cards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()
        if not cards:
            return []

        card_ids = [c.id for c in cards]
        now = datetime.now()
        progresses = db.query(FlashcardProgress).filter(
            FlashcardProgress.student_id == student_id,
            FlashcardProgress.flashcard_id.in_(card_ids)
        ).all()
        
        progress_map = {p.flashcard_id: p for p in progresses}
        
        due_cards = []
        for card in cards:
            prog = progress_map.get(card.id)
            if not prog:
                due_cards.append(card)
            elif prog.next_review_at <= now:
                due_cards.append(card)
                
        return due_cards

    @staticmethod
    def review_card(db: Session, card_id: UUID, student_id: UUID, rating_str: str):
        rating = rating_str.upper()
        if rating not in ["EASY", "GOOD", "HARD", "AGAIN"]:
            raise AppException(status_code=400, error_code="INVALID_RATING", detail="Invalid rating")
            
        prog = db.query(FlashcardProgress).filter(
            FlashcardProgress.student_id == student_id,
            FlashcardProgress.flashcard_id == card_id
        ).first()
        
        if not prog:
            prog = FlashcardProgress(
                student_id=student_id,
                flashcard_id=card_id,
                box_level=0
            )
            db.add(prog)
            
        if rating == "AGAIN":
            prog.box_level = max(0, prog.box_level - 2)
        elif rating == "HARD":
            prog.box_level = max(1, prog.box_level - 1)
        elif rating == "GOOD":
            prog.box_level = min(5, prog.box_level + 1)
        elif rating == "EASY":
            prog.box_level = min(5, prog.box_level + 2)
            
        intervals = {
            0: timedelta(minutes=10),
            1: timedelta(days=1),
            2: timedelta(days=3),
            3: timedelta(days=7),
            4: timedelta(days=14),
            5: timedelta(days=30)
        }
        
        now = datetime.now()
        prog.last_reviewed_at = now
        prog.next_review_at = now + intervals.get(prog.box_level, timedelta(days=30))
        
        db.commit()
        
        return {
            "status": "success",
            "box_level": prog.box_level,
            "next_review_at": prog.next_review_at
        }
