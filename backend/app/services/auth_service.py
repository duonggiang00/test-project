from sqlalchemy.orm import Session
from fastapi import status, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
import os
import uuid

from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.user import UserCreate, ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.token import Token
from app.core.security import get_password_hash, verify_password, create_access_token, create_reset_token, verify_reset_token

class AuthService:
    @staticmethod
    def register(db: Session, user_in: UserCreate) -> User:
        user = db.query(User).filter(User.email == user_in.email).first()
        if user:
            raise AppException(
                status_code=400,
                error_code="USER_ALREADY_EXISTS",
            )
        # SECURITY: Force role to "student" to prevent mass assignment escalation
        new_user = User(
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            full_name=user_in.full_name,
            role="student"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def login(db: Session, form_data: OAuth2PasswordRequestForm) -> dict:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_CREDENTIALS",
            )
        access_token = create_access_token(subject=user.id)
        return {"access_token": access_token, "token_type": "bearer", "user": user}

    @staticmethod
    def forgot_password(db: Session, req: ForgotPasswordRequest) -> dict:
        user = db.query(User).filter(User.email == req.email).first()
        if not user:
            # Prevent user enumeration by always returning success
            return {"message": "If the email exists, a reset link has been sent."}
        
        reset_token = create_reset_token(email=user.email)
        reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
        
        # In a real app, send this via email. For now, log it.
        print(f"\n[{user.email}] PASSWORD RESET LINK: {reset_link}\n")
        
        return {"message": "If the email exists, a reset link has been sent."}

    @staticmethod
    def reset_password(db: Session, req: ResetPasswordRequest) -> dict:
        email = verify_reset_token(req.token)
        if not email:
            raise AppException(status_code=400, error_code="INVALID_OR_EXPIRED_TOKEN")
            
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise AppException(status_code=404, error_code="USER_NOT_FOUND")
            
        user.password_hash = get_password_hash(req.new_password)
        db.commit()
        return {"message": "Password has been reset successfully."}
