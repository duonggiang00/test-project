import sys
import os
import argparse
from sqlalchemy.orm import Session

# Add the app directory to the system path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def seed_teacher(email: str = "teacher@example.com", password: str = "password123", full_name: str = "Test Teacher"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists. Updating password and role to teacher.")
            user.hashed_password = get_password_hash(password)
            user.role = "teacher"
            user.full_name = full_name
        else:
            print(f"Creating new teacher user: {email}")
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                role="teacher",
                full_name=full_name
            )
            db.add(user)
        db.commit()
        print("Teacher seeded successfully!")
    except Exception as e:
        print(f"Error seeding teacher: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed a test teacher account")
    parser.add_argument("--email", default="teacher@example.com", help="Email of the teacher")
    parser.add_argument("--password", default="password123", help="Password of the teacher")
    parser.add_argument("--name", default="Test Teacher", help="Full name of the teacher")
    args = parser.parse_args()
    
    seed_teacher(args.email, args.password, args.name)
