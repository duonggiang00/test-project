from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.correlation import get_current_request_id, new_correlation_id
from app.core.exceptions import AppException
from app.core.security import create_access_token
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.services.audit_service import AuditService


class AuthSessionService:
    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _new_refresh_session(
        user: User,
        *,
        remember_me: bool,
        family_id: uuid.UUID | None = None,
    ) -> tuple[RefreshSession, str]:
        raw_token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        ttl_days = (
            settings.REFRESH_TOKEN_REMEMBER_DAYS
            if remember_me
            else settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        session = RefreshSession(
            id=uuid.uuid4(),
            family_id=family_id or uuid.uuid4(),
            user_id=user.id,
            token_hash=AuthSessionService._hash_token(raw_token),
            remember_me=remember_me,
            created_at=now,
            expires_at=now + timedelta(days=ttl_days),
        )
        return session, raw_token

    @staticmethod
    def issue(db: Session, user: User, *, remember_me: bool) -> dict[str, object]:
        refresh_session, refresh_token = AuthSessionService._new_refresh_session(
            user,
            remember_me=remember_me,
        )
        db.add(refresh_session)
        db.flush()
        return {
            "access_token": create_access_token(
                user.id,
                session_family_id=refresh_session.family_id,
            ),
            "refresh_token": refresh_token,
            "access_expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_expires_in": (
                settings.REFRESH_TOKEN_REMEMBER_DAYS
                if remember_me
                else settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
            * 24
            * 60
            * 60,
            "token_type": "bearer",
            "user": user,
        }

    @staticmethod
    def _load_user_including_deleted(db: Session, user_id: uuid.UUID) -> User | None:
        return db.scalar(
            select(User)
            .where(User.id == user_id)
            .execution_options(include_deleted=True)
        )

    @staticmethod
    def _record_revocation(
        db: Session,
        *,
        user: User,
        reason: str,
        affected_sessions: int,
        actor: User | None = None,
        system_actor: bool = False,
    ) -> None:
        audit_actor = (
            AuditActor(actor_type="system", user_id=None, role="system")
            if system_actor
            else AuditActor(
                actor_type="user",
                user_id=(actor or user).id,
                role=(actor or user).role,
            )
        )
        AuditService.record(
            db,
            AuditEventCreate(
                request_id=get_current_request_id() or new_correlation_id(),
                actor=audit_actor,
                action="auth.sessions_revoked",
                entity=AuditEntity(type="user", id=str(user.id), owner_id=None),
                outcome="success",
                changes={},
                metadata={
                    "reason": reason,
                    "affected_sessions": affected_sessions,
                },
            ),
        )

    @staticmethod
    def _record_replay(
        db: Session,
        *,
        user: User,
        refresh_session: RefreshSession,
    ) -> None:
        AuditService.record(
            db,
            AuditEventCreate(
                request_id=get_current_request_id() or new_correlation_id(),
                actor=AuditActor(
                    actor_type="user",
                    user_id=user.id,
                    role=user.role,
                ),
                action="auth.refresh_replay",
                entity=AuditEntity(
                    type="refresh_session",
                    id=str(refresh_session.id),
                    owner_id=user.id,
                ),
                outcome="success",
                changes={},
                metadata={},
            ),
        )

    @staticmethod
    def revoke_all_for_user(
        db: Session,
        user: User,
        *,
        reason: str,
        actor: User | None = None,
        system_actor: bool = False,
    ) -> int:
        now = datetime.now(timezone.utc)
        result = db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user.id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        affected = int(getattr(result, "rowcount", 0) or 0)
        AuthSessionService._record_revocation(
            db,
            user=user,
            reason=reason,
            affected_sessions=affected,
            actor=actor,
            system_actor=system_actor,
        )
        return affected

    @staticmethod
    def _revoke_family(db: Session, family_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        result = db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    @staticmethod
    def refresh(db: Session, raw_token: str) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        refresh_session = db.scalar(
            select(RefreshSession)
            .where(
                RefreshSession.token_hash
                == AuthSessionService._hash_token(raw_token)
            )
            .with_for_update()
        )
        if refresh_session is None:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_REFRESH_TOKEN",
            )

        user = AuthSessionService._load_user_including_deleted(
            db,
            refresh_session.user_id,
        )
        if user is None:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_REFRESH_TOKEN",
            )

        if refresh_session.revoked_at is not None:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="REFRESH_TOKEN_REVOKED",
            )
        if refresh_session.expires_at <= now:
            refresh_session.revoked_at = now
            db.commit()
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="REFRESH_TOKEN_EXPIRED",
            )
        if refresh_session.rotated_at is not None:
            elapsed = (now - refresh_session.rotated_at).total_seconds()
            if elapsed > settings.REFRESH_TOKEN_RACE_SECONDS:
                affected = AuthSessionService._revoke_family(
                    db,
                    refresh_session.family_id,
                )
                AuthSessionService._record_revocation(
                    db,
                    user=user,
                    reason="refresh_replay",
                    affected_sessions=affected,
                )
                AuthSessionService._record_replay(
                    db,
                    user=user,
                    refresh_session=refresh_session,
                )
                db.commit()
                raise AppException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    error_code="REFRESH_TOKEN_REPLAYED",
                )
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="REFRESH_TOKEN_ALREADY_ROTATED",
            )
        if not user.is_active or user.deleted_at is not None:
            AuthSessionService.revoke_all_for_user(
                db,
                user,
                reason="inactive_user",
                system_actor=True,
            )
            db.commit()
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="ACCOUNT_DISABLED",
            )

        replacement, replacement_token = AuthSessionService._new_refresh_session(
            user,
            remember_me=bool(refresh_session.remember_me),
            family_id=refresh_session.family_id,
        )
        # Materialize the replacement before linking the self-referential FK.
        # The row lock remains held until commit, so rotation stays atomic.
        db.add(replacement)
        db.flush()
        refresh_session.rotated_at = now
        refresh_session.replaced_by_id = replacement.id
        db.commit()
        return {
            "access_token": create_access_token(
                user.id,
                session_family_id=refresh_session.family_id,
            ),
            "refresh_token": replacement_token,
            "access_expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_expires_in": int(
                (replacement.expires_at - now).total_seconds()
            ),
            "token_type": "bearer",
            "user": user,
        }

    @staticmethod
    def logout_current(db: Session, raw_token: str) -> None:
        refresh_session = db.scalar(
            select(RefreshSession)
            .where(
                RefreshSession.token_hash
                == AuthSessionService._hash_token(raw_token)
            )
            .with_for_update()
        )
        if refresh_session is None:
            return
        user = AuthSessionService._load_user_including_deleted(
            db,
            refresh_session.user_id,
        )
        if user is None:
            return
        affected = AuthSessionService._revoke_family(
            db,
            refresh_session.family_id,
        )
        AuthSessionService._record_revocation(
            db,
            user=user,
            reason="logout_current",
            affected_sessions=affected,
        )
        db.commit()

    @staticmethod
    def logout_all(db: Session, user: User) -> None:
        AuthSessionService.revoke_all_for_user(
            db,
            user,
            reason="logout_all",
        )
        db.commit()
