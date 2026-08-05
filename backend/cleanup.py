from app.db.session import SessionLocal
from app.models.exam import Exam
from app.models.user import User
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.flashcard import FlashcardDeck, Flashcard

db = SessionLocal()
db.query(Exam).filter(Exam.title.ilike('%Mock%')).delete(synchronize_session=False)
db.query(Exam).filter(Exam.title == 'Math 101').delete(synchronize_session=False)
db.query(User).filter(User.email.like('%@example.com')).delete(synchronize_session=False)
db.commit()
print("Cleaned up mock data")
