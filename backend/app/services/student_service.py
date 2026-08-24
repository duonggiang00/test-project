from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from datetime import datetime, timezone
import re
from random import SystemRandom
from typing import Any, Optional, cast

from app.core.correlation import get_current_request_id, new_correlation_id
from app.models.exam import Exam, Question
from app.models.enums import QuestionType
from app.models.submission import Submission, SubmissionAnswer
from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.schemas.student import SubmitExamRequest, SubmitExamResponse, StudentExamResultResponse, StudentExamResultAnswer
from app.services.audit_service import AuditService
from app.services.grading_service import GradingService
from app.core.exceptions import AppException
from app.services.content_visibility import StudentContentVisibility

_secure_random = SystemRandom()


def _question_type_value(question: Question) -> str:
    question_type = question.question_type
    if isinstance(question_type, QuestionType):
        return question_type.value
    return str(question_type)


def _student_interaction_metadata(question: Question) -> dict[str, Any] | None:
    """Return only the metadata needed to answer a question.

    Persisted metadata contains the grading key for matching and fill-in-blank
    questions. The pre-submission contract must never serialize those answers.
    """

    metadata: dict[str, Any] = (
        cast(dict[str, Any], question.metadata_json)
        if isinstance(question.metadata_json, dict)
        else {}
    )
    question_type = _question_type_value(question)

    if question_type == QuestionType.FILL_IN_BLANK.value:
        blanks = metadata.get("blanks")
        declared_count = len(blanks) if isinstance(blanks, list) else 0
        token_count = len(re.findall(r"\[BLANK\]|_{3,}", cast(str, question.content)))
        return {"blank_count": max(1, declared_count, token_count)}

    if question_type == QuestionType.MATCHING.value:
        raw_pairs = metadata.get("pairs")
        pairs = [
            pair
            for pair in raw_pairs
            if isinstance(pair, dict)
            and isinstance(pair.get("left"), str)
            and isinstance(pair.get("right"), str)
        ] if isinstance(raw_pairs, list) else []
        left_options = [pair["left"] for pair in pairs]
        right_options = [pair["right"] for pair in pairs]

        # Independent CSPRNG shuffles remove any positional relationship to the
        # persisted answer-key pairs, including across repeated start requests.
        _secure_random.shuffle(left_options)
        _secure_random.shuffle(right_options)

        return {
            "left_options": left_options,
            "right_options": right_options,
        }

    return None


def _student_question_payload(question: Question) -> dict[str, Any]:
    return {
        "id": question.id,
        "content": question.content,
        "points": question.points,
        "question_type": _question_type_value(question),
        "metadata_json": _student_interaction_metadata(question),
        "options": question.options,
    }

class StudentService:
    @staticmethod
    def get_available_exams(db: Session, current_user_id: UUID, search: Optional[str] = None):
        query = StudentContentVisibility.exam_statement().options(
            selectinload(Exam.topic),
            selectinload(Exam.questions),
        )
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
                "topic_name": exam.topic.name if exam.topic else None,
                "question_count": len(exam.questions),
                "max_score": float(sum(question.points for question in exam.questions)),
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
        
        active_submission = existing_sub
        if active_submission is None:
            active_submission = Submission(
                exam_id=exam.id,
                student_id=current_user_id,
                status="in_progress"
            )
            db.add(active_submission)
            try:
                db.commit()
                db.refresh(active_submission)
            except IntegrityError:
                # A concurrent start for the same Student/Exam may win the
                # unique constraint between our read and insert. Reuse that
                # canonical row instead of leaking a database error.
                db.rollback()
                active_submission = db.scalar(
                    select(Submission).where(
                        Submission.exam_id == exam.id,
                        Submission.student_id == current_user_id,
                    )
                )
                if active_submission is None:
                    raise
                if active_submission.status == "submitted":
                    raise AppException(
                        status_code=400,
                        error_code="ALREADY_SUBMITTED",
                    )
        elif active_submission.status == "submitted":
            raise AppException(status_code=400, error_code="ALREADY_SUBMITTED")

        start_time = active_submission.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(
            0,
            int((datetime.now(timezone.utc) - start_time).total_seconds()),
        )
        remaining_seconds = max(
            0,
            exam.duration_minutes * 60 - elapsed_seconds,
        )

        return {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "duration_minutes": exam.duration_minutes,
            "remaining_seconds": remaining_seconds,
            "questions": [
                _student_question_payload(question)
                for question in exam.questions
            ],
        }

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
            ).with_for_update()
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
        answer_map = {answer.question_id: answer for answer in submission.answers}
        answers_response = []

        for question in exam.questions:
            answer = answer_map.get(question.id)
            if answer is not None and answer.is_correct:
                correct_count += 1
            else:
                incorrect_count += 1

            answers_response.append(
                StudentExamResultAnswer(
                    question_id=question.id,
                    content=question.content,
                    question_type=question.question_type,
                    metadata_json=question.metadata_json,
                    options=question.options,
                    answer_data=answer.answer_data if answer else None,
                    is_correct=bool(answer and answer.is_correct),
                    points_awarded=answer.points_awarded if answer else 0.0,
                    points=question.points,
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
