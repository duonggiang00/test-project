import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_users():
    db = SessionLocal()
    try:
        # Admin User
        admin_email = "admin@example.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                password_hash=get_password_hash("12345678"),
                full_name="System Admin",
                role="admin"
            )
            db.add(admin)
        else:
            admin.password_hash = get_password_hash("12345678")
            admin.role = "admin"

        # Student User
        student_email = "student@example.com"
        student = db.query(User).filter(User.email == student_email).first()
        if not student:
            student = User(
                email=student_email,
                password_hash=get_password_hash("12345678"),
                full_name="Test Student",
                role="student"
            )
            db.add(student)
        else:
            student.password_hash = get_password_hash("12345678")
            student.role = "student"

        db.commit()
        print("Success: admin@example.com and student@example.com created/updated.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_users()
