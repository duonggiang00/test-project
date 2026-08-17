from fastapi import Depends, status
from sqlalchemy import select
from app.core.exceptions import AppException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.core.security import ALGORITHM
from app.schemas.token import TokenData
from app.core.permissions import (
    Permission,
    require_permission,
    require_student_self_service,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        # We stored the user id in the 'sub' field of the payload
        token_data = TokenData(user_id=payload.get("sub"))
    except (JWTError, ValidationError):
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.scalar(
        select(User)
        .where(User.id == token_data.user_id)
        .with_for_update(read=True)
    )
    if not user:
        raise AppException(status_code=404, error_code="USER_NOT_FOUND")
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user

def get_current_active_teacher(
    current_user: User = Depends(get_current_user),
) -> User:
    require_permission(current_user, Permission.CREATE_CONTENT)
    return current_user


def get_current_user_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    require_permission(current_user, Permission.MANAGE_USERS)
    return current_user


def get_current_active_student(
    current_user: User = Depends(get_current_user),
) -> User:
    require_student_self_service(current_user, Permission.READ_ASSIGNED_CONTENT)
    return current_user

def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    require_permission(current_user, Permission.ADMIN_OVERRIDE)
    return current_user
