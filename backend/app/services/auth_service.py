from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.correlation import get_current_request_id, new_correlation_id
from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    create_reset_token,
    get_password_hash,
    verify_password,
    verify_reset_token,
)
from app.models.user import User
from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.schemas.user import ForgotPasswordRequest, ResetPasswordRequest, UserCreate
from app.services.audit_service import AuditService
from app.services.auth_session_service import AuthSessionService
from app.services.password_reset_delivery import (
    PasswordResetDelivery,
    password_reset_delivery,
)

class AuthService:
    @staticmethod
    def register(db: Session, user_in: UserCreate) -> User:
        user = db.scalar(select(User).where(User.email == user_in.email))
        if user:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                error_code="USER_ALREADY_EXISTS",
            )
        # SECURITY: Force role to "student" to prevent mass assignment escalation
        new_user = User(
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            full_name=user_in.full_name,
            role="student"
        )
        try:
            db.add(new_user)
            db.flush()
            # Self-registration has no authenticated actor yet -- the
            # system records its own account-creation action, matching
            # user.create's registered policy (success_roles includes
            # "system").
            AuditService.record(
                db,
                AuditEventCreate(
                    request_id=(
                        get_current_request_id() or new_correlation_id()
                    ),
                    actor=AuditActor(
                        actor_type="system",
                        user_id=None,
                        role="system",
                    ),
                    action="user.create",
                    entity=AuditEntity(
                        type="user",
                        id=str(new_user.id),
                        owner_id=None,
                    ),
                    outcome="success",
                    changes={"role": {"before": None, "after": "student"}},
                    metadata={},
                ),
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                error_code="USER_ALREADY_EXISTS",
            ) from exc
        except Exception:
            db.rollback()
            raise
        db.refresh(new_user)
        return new_user

    @staticmethod
    def login(
        db: Session,
        form_data: OAuth2PasswordRequestForm,
        *,
        remember_me: bool = False,
    ) -> dict:
        user = db.scalar(select(User).where(User.email == form_data.username))
        if not user or not verify_password(form_data.password, user.password_hash):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_CREDENTIALS",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="ACCOUNT_DISABLED",
            )
        try:
            tokens = AuthSessionService.issue(
                db,
                user,
                remember_me=remember_me,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        return tokens

    @staticmethod
    def forgot_password(
        db: Session,
        req: ForgotPasswordRequest,
        delivery: PasswordResetDelivery = password_reset_delivery,
    ) -> dict:
        user = db.scalar(select(User).where(User.email == req.email))
        if not user:
            # Prevent user enumeration by always returning success
            return {"message": "If the email exists, a reset link has been sent."}
        
        reset_token = create_reset_token(email=user.email)
        reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
        
        delivery.deliver(email=user.email, reset_link=reset_link)
        
        return {"message": "If the email exists, a reset link has been sent."}

    @staticmethod
    def reset_password(db: Session, req: ResetPasswordRequest) -> dict:
        email = verify_reset_token(req.token)
        if not email:
            raise AppException(status_code=400, error_code="INVALID_OR_EXPIRED_TOKEN")
            
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            raise AppException(status_code=404, error_code="USER_NOT_FOUND")
            
        try:
            user.password_hash = get_password_hash(req.new_password)
            AuthSessionService.revoke_all_for_user(
                db,
                user,
                reason="password_reset",
                system_actor=True,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        return {"message": "Password has been reset successfully."}
