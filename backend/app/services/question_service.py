from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from app.models.exam import Question, Option
from app.models.user import User
from app.schemas.question import QuestionBase, QuestionUpdate
from app.core.exceptions import AppException

class QuestionService:
    @staticmethod
    def get_questions_query(db: Session, topic_id: Optional[UUID] = None, difficulty: Optional[str] = None, search: Optional[str] = None):
        query = db.query(Question).options(selectinload(Question.options))
        if topic_id:
            query = query.filter(Question.topic_id == topic_id)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty.upper())
        if search:
            query = query.filter(Question.content.ilike(f"%{search}%"))
        return query

    @staticmethod
    def create_question(db: Session, question_in: QuestionBase, current_user: User) -> Question:
        question = Question(
            content=question_in.content,
            points=question_in.points,
            question_type=question_in.question_type,
            difficulty=question_in.difficulty,
            topic_id=question_in.topic_id,
            metadata_json=question_in.metadata_json,
            is_ai_generated=False
        )
        db.add(question)
        db.flush()
        
        for opt in question_in.options:
            option = Option(
                question_id=question.id,
                content=opt.content,
                is_correct=opt.is_correct
            )
            db.add(option)
            
        db.commit()
        
        fetched_q = db.query(Question).options(selectinload(Question.options)).filter(Question.id == question.id).first()
        return fetched_q

    @staticmethod
    def get_question(db: Session, question_id: UUID, current_user: User) -> Question:
        question = db.query(Question).options(selectinload(Question.options)).filter(Question.id == question_id).first()
        if not question:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")
        return question

    @staticmethod
    def update_question(db: Session, question_id: UUID, question_in: QuestionUpdate, current_user: User) -> Question:
        question = db.query(Question).options(selectinload(Question.options)).filter(Question.id == question_id).first()
        if not question:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")
            
        if question_in.content is not None:
            question.content = question_in.content
        if question_in.points is not None:
            question.points = question_in.points
        if question_in.question_type is not None:
            question.question_type = question_in.question_type
        if question_in.difficulty is not None:
            question.difficulty = question_in.difficulty
        if question_in.topic_id is not None:
            question.topic_id = question_in.topic_id
        if question_in.metadata_json is not None:
            question.metadata_json = question_in.metadata_json
            
        if question_in.options is not None:
            db.query(Option).filter(Option.question_id == question.id).delete()
            for opt in question_in.options:
                db.add(Option(question_id=question.id, content=opt.content, is_correct=opt.is_correct))
                
        db.commit()
        fetched_q = db.query(Question).options(selectinload(Question.options)).filter(Question.id == question.id).first()
        return fetched_q

    @staticmethod
    def delete_question(db: Session, question_id: UUID, current_user: User):
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise AppException(status_code=404, error_code="QUESTION_NOT_FOUND")
            
        db.delete(question)
        db.commit()
