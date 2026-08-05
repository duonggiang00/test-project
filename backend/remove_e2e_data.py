import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.exam import Exam, Question, Option
from app.models.topic import Topic
from app.models.material import StudyMaterial
from app.models.flashcard import FlashcardDeck, Flashcard
from app.models.user import User

def remove_e2e_data():
    db = SessionLocal()
    try:
        keywords = ['%test%', '%mock%', '%e2e%']
        
        # 1. Clean Exams
        exams = []
        for kw in keywords:
            exams.extend(db.query(Exam).filter(Exam.title.ilike(kw)).all())
        
        deleted_exams = 0
        for exam in set(exams):
            # Delete questions & options for this exam
            for q in db.query(Question).filter(Question.exam_id == exam.id).all():
                db.query(Option).filter(Option.question_id == q.id).delete(synchronize_session=False)
            db.query(Question).filter(Question.exam_id == exam.id).delete(synchronize_session=False)
            db.delete(exam)
            deleted_exams += 1
            
        # 2. Clean Topics
        topics = []
        for kw in keywords:
            topics.extend(db.query(Topic).filter(Topic.name.ilike(kw)).all())
            
        deleted_topics = 0
        for topic in set(topics):
            db.delete(topic)
            deleted_topics += 1
            
        # 3. Clean Materials
        materials = []
        for kw in keywords:
            materials.extend(db.query(StudyMaterial).filter(StudyMaterial.title.ilike(kw)).all())
            
        deleted_materials = 0
        for material in set(materials):
            db.delete(material)
            deleted_materials += 1
            
        db.commit()
        print(f"Cleared E2E Data: {deleted_exams} Exams, {deleted_topics} Topics, {deleted_materials} Materials.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    remove_e2e_data()
