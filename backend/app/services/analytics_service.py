from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import statistics
from collections import defaultdict

from app.models.user import User
from app.models.exam import Exam, Question
from app.models.submission import Submission
from app.models.topic import Topic

class AnalyticsService:
    @staticmethod
    def get_overview(db: Session):
        total_students = db.query(User).filter(User.role == "student").count()
        total_exams = db.query(Exam).count()
        total_questions = db.query(Question).count()
        total_topics = db.query(Topic).count()
        total_submissions = db.query(Submission).count()
        
        completed_submissions = db.query(Submission).filter(Submission.status == "submitted").all()
        completed_count = len(completed_submissions)
        
        completion_rate = (completed_count / total_submissions * 100.0) if total_submissions > 0 else 0.0
        scores = [s.total_score for s in completed_submissions if s.total_score is not None]
        overall_avg_score = float(statistics.mean(scores)) if scores else 0.0
        
        return {
            "total_students": total_students,
            "total_exams": total_exams,
            "total_questions": total_questions,
            "total_submissions": total_submissions,
            "total_topics": total_topics,
            "overall_avg_score": round(overall_avg_score, 2),
            "completion_rate": round(completion_rate, 2),
            "pass_rate": round(completion_rate, 2)
        }

    @staticmethod
    def get_score_stats(db: Session, exam_id: Optional[UUID] = None, topic_id: Optional[UUID] = None):
        query = db.query(Submission).filter(Submission.status == "submitted")
        if exam_id:
            query = query.filter(Submission.exam_id == exam_id)
        if topic_id:
            query = query.join(Exam, Submission.exam_id == Exam.id).filter(Exam.topic_id == topic_id)
            
        submissions = query.all()
        if not submissions:
            return {
                "highest_score": 0.0,
                "lowest_score": 0.0,
                "average_score": 0.0,
                "median_score": 0.0,
                "distribution": [
                    {"range_label": "0-20%", "count": 0},
                    {"range_label": "21-40%", "count": 0},
                    {"range_label": "41-60%", "count": 0},
                    {"range_label": "61-80%", "count": 0},
                    {"range_label": "81-100%", "count": 0},
                ]
            }
            
        scores = [s.total_score for s in submissions if s.total_score is not None]
        if not scores:
            scores = [0.0]

        highest_score = float(max(scores))
        lowest_score = float(min(scores))
        average_score = float(statistics.mean(scores))
        median_score = float(statistics.median(scores))
        
        buckets = {"0-20%": 0, "21-40%": 0, "41-60%": 0, "61-80%": 0, "81-100%": 0}
        for sc in scores:
            if sc <= 20:
                buckets["0-20%"] += 1
            elif sc <= 40:
                buckets["21-40%"] += 1
            elif sc <= 60:
                buckets["41-60%"] += 1
            elif sc <= 80:
                buckets["61-80%"] += 1
            else:
                buckets["81-100%"] += 1
                
        distribution = [{"range_label": k, "count": v} for k, v in buckets.items()]
        
        return {
            "highest_score": round(highest_score, 2),
            "lowest_score": round(lowest_score, 2),
            "average_score": round(average_score, 2),
            "median_score": round(median_score, 2),
            "distribution": distribution
        }

    @staticmethod
    def get_completion_status(db: Session, exam_id: Optional[UUID] = None):
        query = db.query(Submission)
        if exam_id:
            query = query.filter(Submission.exam_id == exam_id)
            
        submissions = query.all()
        completed = sum(1 for s in submissions if s.status == "submitted")
        in_progress = sum(1 for s in submissions if s.status == "in_progress")
        total = len(submissions)
        
        return {
            "completed": completed,
            "in_progress": in_progress,
            "completed_count": completed,
            "in_progress_count": in_progress,
            "not_started_count": 0,
            "total_assigned": total
        }

    @staticmethod
    def get_topic_performance(db: Session):
        topics = db.query(Topic).all()
        topic_ids = [t.id for t in topics]

        subs = (
            db.query(Submission, Exam.topic_id)
            .join(Exam, Submission.exam_id == Exam.id)
            .filter(Exam.topic_id.in_(topic_ids), Submission.status == "submitted")
            .all()
        )

        scores_by_topic = defaultdict(list)
        for sub, topic_id in subs:
            if sub.total_score is not None:
                scores_by_topic[topic_id].append(sub.total_score)

        res = []
        for topic in topics:
            scores = scores_by_topic.get(topic.id, [])
            avg_score = float(statistics.mean(scores)) if scores else 0.0
            res.append({
                "topic_id": topic.id,
                "topic_name": topic.name,
                "avg_score_percentage": round(avg_score, 2),
                "total_attempts": len(scores)
            })
        return res
