from fastapi import Depends, status
from datetime import datetime, timezone

from sqlalchemy import select
from app.core.exceptions import AppException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.session import get_db
from app.models.user import User
from app.models.refresh_session import RefreshSession
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
        token_data = TokenData(
            user_id=payload.get("sub"),
            session_family_id=payload.get("sid"),
            token_type=payload.get("type"),
        )
    except (JWTError, ValidationError):
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_data.token_type != "access" or token_data.session_family_id is None:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.scalar(
        select(User)
        .join(RefreshSession, RefreshSession.user_id == User.id)
        .where(
            User.id == token_data.user_id,
            User.is_active.is_(True),
            RefreshSession.family_id == token_data.session_family_id,
            RefreshSession.rotated_at.is_(None),
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(timezone.utc),
        )
        .with_for_update(of=User, read=True)
        .limit(1)
    )
    if not user:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
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
