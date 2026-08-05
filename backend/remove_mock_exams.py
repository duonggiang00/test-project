import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.exam import Exam, Question, Option
from app.models.submission import Submission, SubmissionAnswer
from app.models.user import User
from app.models.topic import Topic
from app.models.material import StudyMaterial

def remove_mock():
    db = SessionLocal()
    try:
        # Find exams that have NO topic or NO questions, or title contains 'Mock' or 'Test'
        exams = db.query(Exam).all()
        deleted_count = 0
        for exam in exams:
            q_count = db.query(Question).filter(Question.exam_id == exam.id).count()
            if q_count == 0 or exam.topic_id is None or 'mock' in exam.title.lower():
                print(f"Deleting exam: {exam.title} (ID: {exam.id}, Questions: {q_count}, Topic: {exam.topic_id})")
                # Delete submissions first
                db.query(Submission).filter(Submission.exam_id == exam.id).delete()
                # Delete the exam itself
                db.delete(exam)
                deleted_count += 1
        
        db.commit()
        print(f"Successfully deleted {deleted_count} mock/empty exams.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    remove_mock()
