import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import verify_password

db = SessionLocal()
user = db.query(User).filter(User.email=="admin@example.com").first()
if user:
    try:
        is_valid = verify_password("12345678", user.password_hash)
        print("Password valid:", is_valid)
    except Exception as e:
        print("Error verifying password:", e)
else:
    print("User not found.")
