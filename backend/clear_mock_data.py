import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.submission import Submission
from app.models.exam import Option, Question, Exam
from app.models.topic import Topic
from app.models.material import StudyMaterial
from app.models.user import User

def clear_data():
    db = SessionLocal()
    try:
        # Delete in order of foreign key dependencies
        db.query(Submission).delete()
        db.query(Option).delete()
        db.query(Question).delete()
        db.query(Exam).delete()
        db.query(Topic).delete()
        db.query(StudyMaterial).delete()
        db.query(User).delete()
        db.commit()
        print("All data cleared successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error clearing data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_data()
