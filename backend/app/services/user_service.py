from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session
from fastapi import UploadFile
from uuid import UUID
import os
import uuid

from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.user import UserUpdate, PasswordUpdate
from app.core.security import get_password_hash, verify_password
from app.db.soft_delete import is_restorable, soft_delete
from app.models.exam import Exam, Question
from app.models.flashcard import FlashcardProgress
from app.models.material import StudyMaterial
from app.models.submission import Submission
from app.models.topic import Topic
from app.core.permissions import Permission, require_permission
from app.services.authorization_service import AuthorizationService

class UserService:
    @staticmethod
    def get_all_users_query(db: Session):
        return select(User).order_by(User.created_at.desc(), User.id)

    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> User:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise AppException(status_code=404, error_code="USER_NOT_FOUND")
        return user

    @staticmethod
    def _get_user_for_update(db: Session, user_id: UUID) -> User:
        user = db.scalar(
            select(User).where(User.id == user_id).with_for_update()
        )
        if user is None:
            raise AppException(status_code=404, error_code="USER_NOT_FOUND")
        return user

    @staticmethod
    def update_user_role(
        db: Session,
        user_id: UUID,
        new_role: str,
        actor: User,
    ) -> User:
        if new_role not in ["student", "teacher", "admin"]:
            raise AppException(status_code=400, error_code="INVALID_ROLE")

        if new_role == "admin":
            require_permission(actor, Permission.ADMIN_OVERRIDE)

        user = UserService._get_user_for_update(db, user_id)
        if user.role == "admin":
            require_permission(actor, Permission.ADMIN_OVERRIDE)
        if new_role == "student" and UserService._has_owned_or_retained_data(
            db,
            user.id,
        ):
            raise AppException(
                status_code=409,
                error_code="USER_ROLE_CHANGE_BLOCKED_BY_OWNED_DATA",
            )
        
        before_role = user.role
        user.role = new_role
        AuthorizationService.commit_with_audit(
            db,
            actor=actor,
            entity_type="user",
            entity_id=user.id,
            owner_id=None,
            action="user.role_change",
            changes={"role": {"before": before_role, "after": new_role}},
        )
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: UUID, actor: User) -> dict:
        user = UserService._get_user_for_update(db, user_id)
        if UserService._has_owned_or_retained_data(db, user.id):
            raise AppException(
                status_code=409,
                error_code="USER_DELETE_BLOCKED_BY_RETAINED_DATA",
            )

        soft_delete(user, actor.id)
        AuthorizationService.commit_with_audit(
            db,
            actor=actor,
            entity_type="user",
            entity_id=user.id,
            owner_id=None,
            action="user.disable",
        )
        return {"message": "User deleted successfully"}

    @staticmethod
    def restore_user(db: Session, user_id: UUID, actor: User) -> User:
        user = db.scalar(
            select(User)
            .where(User.id == user_id, User.deleted_at.is_not(None))
            .execution_options(include_deleted=True)
            .with_for_update()
        )
        if user is None:
            raise AppException(status_code=404, error_code="USER_NOT_FOUND")

        if not is_restorable(user.deleted_at):
            raise AppException(
                status_code=409,
                error_code="USER_RESTORE_WINDOW_EXPIRED",
            )

        deleted_at_before = user.deleted_at
        user.deleted_at = None
        user.deleted_by_id = None

        # Users have no owner concept; passing owner_id=None means
        # evaluate_owned_resource only allows an admin actor here.
        AuthorizationService.commit_restore(
            db,
            actor=actor,
            permission=Permission.RESTORE_OWNED_CONTENT,
            entity_type="user",
            entity_id=user.id,
            owner_id=None,
            deleted_at_before=deleted_at_before,
        )
        db.refresh(user)
        return user

    @staticmethod
    def _has_owned_or_retained_data(db: Session, user_id: UUID) -> bool:
        return bool(
            db.scalar(
                select(
                    or_(
                        exists(select(Topic.id).where(Topic.owner_id == user_id)),
                        exists(select(Exam.id).where(Exam.creator_id == user_id)),
                        exists(
                            select(Question.id).where(Question.owner_id == user_id)
                        ),
                        exists(
                            select(StudyMaterial.id).where(
                                StudyMaterial.uploader_id == user_id
                            )
                        ),
                        exists(
                            select(Submission.id).where(
                                Submission.student_id == user_id
                            )
                        ),
                        exists(
                            select(FlashcardProgress.id).where(
                                FlashcardProgress.student_id == user_id
                            )
                        ),
                    )
                )
            )
        )

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
