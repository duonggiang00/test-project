from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from app.core.correlation import get_current_request_id, new_correlation_id
from app.models.exam import Exam, Question
from app.models.submission import Submission, SubmissionAnswer
from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.schemas.student import SubmitExamRequest, SubmitExamResponse, StudentExamResultResponse, StudentExamResultAnswer
from app.services.audit_service import AuditService
from app.services.grading_service import GradingService
from app.core.exceptions import AppException
from app.services.content_visibility import StudentContentVisibility

class StudentService:
    @staticmethod
    def get_available_exams(db: Session, current_user_id: UUID, search: Optional[str] = None):
        query = StudentContentVisibility.exam_statement()
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            query = query.where(Exam.title.ilike(f"%{safe_search}%"))
        exams = db.scalars(query.order_by(Exam.created_at.desc(), Exam.id)).all()
        
        exam_ids = [e.id for e in exams]
        submissions = db.scalars(
            select(Submission).where(
                Submission.student_id == current_user_id,
                Submission.exam_id.in_(exam_ids),
            )
        ).all()
        
        sub_map = {s.exam_id: s for s in submissions}
        
        result = []
        for exam in exams:
            sub = sub_map.get(exam.id)
            result.append({
                "id": exam.id,
                "title": exam.title,
                "description": exam.description,
                "duration_minutes": exam.duration_minutes,
                "submission_status": sub.status if sub else None,
                "total_score": sub.total_score if sub else None
            })
        return result

    @staticmethod
    def start_exam(db: Session, current_user_id: UUID, exam_id: UUID):
        exam = db.scalar(
            StudentContentVisibility.exam_statement()
            .options(selectinload(Exam.questions).selectinload(Question.options))
            .where(Exam.id == exam_id)
            .with_for_update(read=True)
        )
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
            
        existing_sub = db.scalar(
            select(Submission).where(
                Submission.exam_id == exam.id,
                Submission.student_id == current_user_id,
            )
        )
        
        if not existing_sub:
            submission = Submission(
                exam_id=exam.id,
                student_id=current_user_id,
                status="in_progress"
            )
            db.add(submission)
            db.commit()
        elif existing_sub.status == "submitted":
            raise AppException(status_code=400, error_code="ALREADY_SUBMITTED")
            
        return exam

    @staticmethod
    def submit_exam(db: Session, current_user_id: UUID, exam_id: UUID, payload: SubmitExamRequest):
        exam = db.scalar(
            StudentContentVisibility.exam_statement()
            .options(selectinload(Exam.questions).selectinload(Question.options))
            .where(Exam.id == exam_id)
        )
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")
            
        submission = db.scalar(
            select(Submission).where(
                Submission.exam_id == exam.id,
                Submission.student_id == current_user_id,
            )
        )
        
        if not submission:
            raise AppException(status_code=400, error_code="NOT_STARTED_YET")
            
        if submission.status == "submitted":
            raise AppException(status_code=400, error_code="ALREADY_SUBMITTED")
            
        start_time = submission.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        duration = (now - start_time).total_seconds() / 60.0
        if duration > (exam.duration_minutes + 2):
            raise AppException(status_code=400, error_code="TIME_LIMIT_EXCEEDED")
            
        total_score = 0.0
        max_score = sum(q.points for q in exam.questions)
        
        q_map = {q.id: q for q in exam.questions}
        
        for answer_in in payload.answers:
            q = q_map.get(answer_in.question_id)
            if not q:
                continue
                
            ans_data = answer_in.answer_data or {}
            if answer_in.selected_option_id:
                ans_data["selected_option_ids"] = [str(answer_in.selected_option_id)]
                ans_data["selected_option_id"] = str(answer_in.selected_option_id)
                
            points_awarded = GradingService.grade_question(q, ans_data)
            is_correct = points_awarded == q.points
            
            total_score += points_awarded
                
            sub_answer = SubmissionAnswer(
                submission_id=submission.id,
                question_id=q.id,
                answer_data=ans_data,
                is_correct=is_correct,
                points_awarded=points_awarded
            )
            db.add(sub_answer)
            
        submission.end_time = now
        submission.total_score = total_score
        submission.status = "submitted"

        try:
            AuditService.record(
                db,
                AuditEventCreate(
                    request_id=(
                        get_current_request_id() or new_correlation_id()
                    ),
                    actor=AuditActor(
                        actor_type="user",
                        user_id=current_user_id,
                        role="student",
                    ),
                    action="submission.graded",
                    entity=AuditEntity(
                        type="submission",
                        id=str(submission.id),
                        owner_id=current_user_id,
                    ),
                    outcome="success",
                    changes={
                        "total_score": {"before": 0.0, "after": total_score}
                    },
                    metadata={"max_score": max_score},
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(submission)
        
        return SubmitExamResponse(
            submission_id=submission.id,
            total_score=total_score,
            max_score=max_score
        )

    @staticmethod
    def get_exam_result(db: Session, current_user_id: UUID, exam_id: UUID):
        exam = db.scalar(
            StudentContentVisibility.exam_statement()
            .options(selectinload(Exam.questions).selectinload(Question.options))
            .where(Exam.id == exam_id)
        )
        
        if not exam:
            raise AppException(status_code=404, error_code="EXAM_NOT_FOUND")

        submission = db.scalar(
            select(Submission)
            .options(selectinload(Submission.answers))
            .where(
                Submission.exam_id == exam.id,
                Submission.student_id == current_user_id,
            )
        )

        if not submission or submission.status != "submitted":
            raise AppException(status_code=400, error_code="NOT_SUBMITTED")

        correct_count = 0
        incorrect_count = 0

        q_map = {q.id: q for q in exam.questions}
        
        answers_response = []
        
        for ans in submission.answers:
            if ans.is_correct:
                correct_count += 1
            else:
                incorrect_count += 1
                
            q = q_map.get(ans.question_id)
            if not q:
                continue
            
            answers_response.append(
                StudentExamResultAnswer(
                    question_id=q.id,
                    content=q.content,
                    question_type=q.question_type,
                    metadata_json=q.metadata_json,
                    options=q.options,
                    answer_data=ans.answer_data,
                    is_correct=ans.is_correct,
                    points_awarded=ans.points_awarded,
                    points=q.points
                )
            )
            
        start_time = submission.start_time
        if start_time and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        end_time = submission.end_time
        if end_time and end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
            
        time_taken = 0
        if start_time and end_time:
            time_taken = int((end_time - start_time).total_seconds())

        return StudentExamResultResponse(
            exam_id=exam.id,
            title=exam.title,
            total_score=submission.total_score or 0.0,
            max_score=sum(q.points for q in exam.questions),
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            time_taken_seconds=time_taken,
            answers=answers_response
        )
