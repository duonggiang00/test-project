from fastapi import APIRouter, Depends
from app.core.exceptions import AppException
from sqlalchemy.orm import Session
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.api.deps import get_current_active_admin, get_current_user_manager
from app.services.user_service import UserService

router = APIRouter()

@router.get("/users", response_model=Page[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user_manager)
):
    return paginate(db, UserService.get_all_users_query(db))

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user_manager)
):
    return UserService.get_user_by_id(db, user_id)

@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    new_role: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user_manager)
):
    return UserService.update_user_role(
        db,
        user_id,
        new_role,
        current_admin,
    )

@router.delete("/users/{user_id}")
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin)
):
    return UserService.delete_user(db, user_id)
