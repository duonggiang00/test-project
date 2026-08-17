from collections import defaultdict
import statistics
from typing import Optional
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import Permission, require_owner_scope
from app.models.exam import Exam, Question
from app.models.submission import Submission
from app.models.topic import Topic
from app.models.user import User


class AnalyticsService:
    @staticmethod
    def _scope(current_user: User):
        return require_owner_scope(
            current_user,
            Permission.READ_OWNED_EXAM_SUBMISSIONS,
        )

    @staticmethod
    def _exam_predicates(current_user: User):
        scope = AnalyticsService._scope(current_user)
        if scope.scoped_owner_id is None:
            return ()
        return (Exam.creator_id == scope.scoped_owner_id,)

    @staticmethod
    def _topic_predicates(current_user: User):
        scope = AnalyticsService._scope(current_user)
        if scope.scoped_owner_id is None:
            return ()
        return (Topic.owner_id == scope.scoped_owner_id,)

    @staticmethod
    def _question_predicates(current_user: User):
        scope = AnalyticsService._scope(current_user)
        if scope.scoped_owner_id is None:
            return ()
        return (
            or_(
                Question.owner_id == scope.scoped_owner_id,
                (
                    Question.owner_id.is_(None)
                    & Question.exam.has(
                        Exam.creator_id == scope.scoped_owner_id
                    )
                ),
            ),
        )

    @staticmethod
    def get_overview(db: Session, current_user: User):
        exam_predicates = AnalyticsService._exam_predicates(current_user)
        topic_predicates = AnalyticsService._topic_predicates(current_user)
        question_predicates = AnalyticsService._question_predicates(current_user)
        scope = AnalyticsService._scope(current_user)

        total_exams = db.scalar(
            select(func.count(Exam.id)).where(*exam_predicates)
        ) or 0
        total_questions = db.scalar(
            select(func.count(Question.id)).where(*question_predicates)
        ) or 0
        total_topics = db.scalar(
            select(func.count(Topic.id)).where(*topic_predicates)
        ) or 0

        submission_metrics = db.execute(
            select(
                func.count(Submission.id),
                func.count(Submission.id).filter(
                    Submission.status == "submitted"
                ),
                func.avg(Submission.total_score).filter(
                    Submission.status == "submitted"
                ),
                func.count(func.distinct(Submission.student_id)),
            )
            .join(Exam, Submission.exam_id == Exam.id)
            .where(*exam_predicates)
        ).one()
        total_submissions = submission_metrics[0] or 0
        completed_count = submission_metrics[1] or 0
        average_score = float(submission_metrics[2] or 0.0)
        scoped_students = submission_metrics[3] or 0
        total_students = (
            db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
            if scope.scoped_owner_id is None
            else scoped_students
        )
        completion_rate = (
            completed_count / total_submissions * 100.0
            if total_submissions
            else 0.0
        )
        return {
            "total_students": total_students,
            "total_exams": total_exams,
            "total_questions": total_questions,
            "total_submissions": total_submissions,
            "total_topics": total_topics,
            "overall_avg_score": round(average_score, 2),
            "completion_rate": round(completion_rate, 2),
            "pass_rate": round(completion_rate, 2),
        }

    @staticmethod
    def get_score_stats(
        db: Session,
        current_user: User,
        exam_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
    ):
        predicates = list(AnalyticsService._exam_predicates(current_user))
        if exam_id:
            predicates.append(Submission.exam_id == exam_id)
        if topic_id:
            predicates.append(Exam.topic_id == topic_id)
        scores = [
            float(score)
            for score in db.scalars(
                select(Submission.total_score)
                .join(Exam, Submission.exam_id == Exam.id)
                .where(Submission.status == "submitted", *predicates)
            ).all()
            if score is not None
        ]
        buckets = {
            "0-20%": 0,
            "21-40%": 0,
            "41-60%": 0,
            "61-80%": 0,
            "81-100%": 0,
        }
        for score in scores:
            if score <= 20:
                buckets["0-20%"] += 1
            elif score <= 40:
                buckets["21-40%"] += 1
            elif score <= 60:
                buckets["41-60%"] += 1
            elif score <= 80:
                buckets["61-80%"] += 1
            else:
                buckets["81-100%"] += 1
        return {
            "highest_score": round(max(scores), 2) if scores else 0.0,
            "lowest_score": round(min(scores), 2) if scores else 0.0,
            "average_score": round(float(statistics.mean(scores)), 2)
            if scores
            else 0.0,
            "median_score": round(float(statistics.median(scores)), 2)
            if scores
            else 0.0,
            "distribution": [
                {"range_label": label, "count": count}
                for label, count in buckets.items()
            ],
        }

    @staticmethod
    def get_completion_status(
        db: Session,
        current_user: User,
        exam_id: Optional[UUID] = None,
    ):
        predicates = list(AnalyticsService._exam_predicates(current_user))
        if exam_id:
            predicates.append(Submission.exam_id == exam_id)
        completed, in_progress, total = db.execute(
            select(
                func.sum(case((Submission.status == "submitted", 1), else_=0)),
                func.sum(case((Submission.status == "in_progress", 1), else_=0)),
                func.count(Submission.id),
            )
            .join(Exam, Submission.exam_id == Exam.id)
            .where(*predicates)
        ).one()
        completed = completed or 0
        in_progress = in_progress or 0
        total = total or 0
        return {
            "completed": completed,
            "in_progress": in_progress,
            "completed_count": completed,
            "in_progress_count": in_progress,
            "not_started_count": 0,
            "total_assigned": total,
        }

    @staticmethod
    def get_topic_performance(db: Session, current_user: User):
        topics = db.scalars(
            select(Topic)
            .where(*AnalyticsService._topic_predicates(current_user))
            .order_by(Topic.name, Topic.id)
        ).all()
        if not topics:
            return []
        topic_ids = [topic.id for topic in topics]
        rows = db.execute(
            select(
                Exam.topic_id,
                func.avg(Submission.total_score),
                func.count(Submission.id),
            )
            .join(Submission, Submission.exam_id == Exam.id)
            .where(
                Exam.topic_id.in_(topic_ids),
                Submission.status == "submitted",
                *AnalyticsService._exam_predicates(current_user),
            )
            .group_by(Exam.topic_id)
        ).all()
        metrics = {
            topic_id: (float(average or 0.0), attempts)
            for topic_id, average, attempts in rows
        }
        return [
            {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "avg_score_percentage": round(
                    metrics.get(topic.id, (0.0, 0))[0],
                    2,
                ),
                "total_attempts": metrics.get(topic.id, (0.0, 0))[1],
            }
            for topic in topics
        ]
