import sys
import os

# Add the parent directory to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models import Exam, Topic

def clean_mocks():
    db = SessionLocal()
    try:
        # Xóa các kỳ thi rác từ kịch bản E2E cũ
        deleted_exams_1 = db.query(Exam).filter(Exam.title.ilike('%E2E%')).delete(synchronize_session=False)
        deleted_exams_2 = db.query(Exam).filter(Exam.title.ilike('%Mock%')).delete(synchronize_session=False)
        
        # Xóa các Topic rác từ kịch bản E2E cũ
        deleted_topics = db.query(Topic).filter(Topic.name.ilike('%E2E%')).delete(synchronize_session=False)
        
        db.commit()
        print(f"✅ Đã xóa {deleted_exams_1 + deleted_exams_2} kỳ thi rác.")
        print(f"✅ Đã xóa {deleted_topics} topic rác.")
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_mocks()
