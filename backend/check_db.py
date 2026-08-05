import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.topic import Topic
from app.models.material import StudyMaterial
from app.models.exam import Exam, Question
from app.models.submission import Submission

def check_db():
    db = SessionLocal()
    try:
        print("--- POSTGRESQL DATABASE RECORDS ---")
        print(f"Users:       {db.query(User).count()}")
        print(f"Topics:      {db.query(Topic).count()}")
        print(f"Exams:       {db.query(Exam).count()}")
        print(f"Questions:   {db.query(Question).count()}")
        print(f"Submissions: {db.query(Submission).count()}")
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
