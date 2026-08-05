from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from app.models.exam import Exam, Question, Option
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate
from app.schemas.question import QuestionBase, QuestionBulkCreate
from app.core.exceptions import AppException

class ExamService:
    @staticmethod
    def get_exams_query(db: Session, search: Optional[str] = None, topic_id: Optional[UUID] = None):
        query = db.query(Exam)
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            query = query.filter(Exam.title.ilike(f"%{safe_search}%"))
        if topic_id:
            query = query.filter(Exam.topic_id == topic_id)
        return query

    @staticmethod
    def create_exam(db: Session, exam_in: ExamCreate, current_user_id: UUID) -> Exam:
        exam = Exam(
            title=exam_in.title,
            description=exam_in.description,
            duration_minutes=exam_in.duration_minutes,
            is_published=exam_in.is_published,
            topic_id=exam_in.topic_id,
            creator_id=current_user_id
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam

    @staticmethod
    def update_exam(db: Session, exam_id: UUID, exam_in: ExamUpdate, current_user: User) -> Exam:
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        if exam.creator_id != current_user.id and current_user.role != "admin":
            raise AppException(status_code=403, error_code="NOT_ENOUGH_PERMISSIONS")
        
        exam.title = exam_in.title
        exam.description = exam_in.description
        exam.duration_minutes = exam_in.duration_minutes
        exam.is_published = exam_in.is_published
        exam.topic_id = exam_in.topic_id
        
        db.commit()
        db.refresh(exam)
        return exam

    @staticmethod
    def delete_exam(db: Session, exam_id: UUID, current_user: User):
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
            
        if exam.creator_id != current_user.id and current_user.role != "admin":
            raise AppException(status_code=403, error_code="NOT_ENOUGH_PERMISSIONS")
            
        db.delete(exam)
        db.commit()

    @staticmethod
    def get_exam(db: Session, exam_id: UUID, current_user: User) -> Exam:
        exam = db.query(Exam).options(
            selectinload(Exam.questions).selectinload(Question.options)
        ).filter(Exam.id == exam_id).first()
        
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
            
        if not exam.is_published and exam.creator_id != current_user.id and current_user.role != "admin":
            raise AppException(status_code=403, error_code="NOT_ENOUGH_PERMISSIONS")
        return exam

    @staticmethod
    def create_question_in_exam(db: Session, exam_id: UUID, question_in: QuestionBase, current_user: User) -> Question:
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
        if exam.creator_id != current_user.id and current_user.role != "admin":
            raise AppException(status_code=403, error_code="NOT_ENOUGH_PERMISSIONS")
            
        question = Question(
            exam_id=exam.id,
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
    def add_questions_to_exam(db: Session, exam_id: UUID, question_in: QuestionBulkCreate, current_user: User) -> int:
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
            
        questions = db.query(Question).filter(Question.id.in_(question_in.question_ids)).all()
        for q in questions:
            q.exam_id = exam.id
            
        db.commit()
        return len(questions)
