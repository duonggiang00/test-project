from sqlalchemy.orm import Session, Query
from fastapi import UploadFile
from uuid import UUID
import os
import uuid

from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.user import UserUpdate, PasswordUpdate
from app.core.security import get_password_hash, verify_password

class UserService:
    @staticmethod
    def get_all_users_query(db: Session) -> Query:
        return db.query(User)

    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException(status_code=404, error_code="USER_NOT_FOUND")
        return user

    @staticmethod
    def update_user_role(db: Session, user_id: UUID, new_role: str) -> User:
        if new_role not in ["student", "teacher", "admin"]:
            raise AppException(status_code=400, error_code="INVALID_ROLE")
            
        user = UserService.get_user_by_id(db, user_id)
        
        user.role = new_role
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: UUID) -> dict:
        user = UserService.get_user_by_id(db, user_id)
        
        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}

    @staticmethod
    def update_profile(db: Session, current_user: User, user_update: UserUpdate) -> User:
        update_data = user_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(current_user, key, value)
        db.commit()
        db.refresh(current_user)
        return current_user

    @staticmethod
    def update_password(db: Session, current_user: User, password_data: PasswordUpdate) -> dict:
        if not verify_password(password_data.old_password, current_user.password_hash):
            raise AppException(
                status_code=400,
                error_code="INCORRECT_OLD_PASSWORD",
            )
        current_user.password_hash = get_password_hash(password_data.new_password)
        db.commit()
        return {"message": "Password updated successfully"}

    @staticmethod
    def upload_avatar(db: Session, current_user: User, file: UploadFile) -> User:
        # Ensure uploads directory exists
        os.makedirs("uploads/avatars", exist_ok=True)
        
        content = file.file.read()
        if len(content) > 5 * 1024 * 1024: # 5MB limit
            raise AppException(status_code=400, error_code="FILE_TOO_LARGE")
            
        # Check magic bytes for PNG/JPEG
        if not (content.startswith(b"\x89PNG\r\n\x1a\n") or content.startswith(b"\xff\xd8\xff")):
            raise AppException(status_code=400, error_code="INVALID_IMAGE_FORMAT")
            
        ext = "png" if content.startswith(b"\x89PNG") else "jpg"
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = f"uploads/avatars/{filename}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
            
        # Construct URL (assuming a static route serves /uploads)
        avatar_url = f"/uploads/avatars/{filename}"
        current_user.avatar_url = avatar_url
        db.commit()
        db.refresh(current_user)
        return current_user
