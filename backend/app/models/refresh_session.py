import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = (
        CheckConstraint(
            "char_length(token_hash) = 64",
            name="ck_refresh_sessions_token_hash_length",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_refresh_sessions_expiry_after_creation",
        ),
        Index(
            "ix_refresh_sessions_family_active",
            "family_id",
            "revoked_at",
            "rotated_at",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    family_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    remember_me = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    replaced_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("refresh_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
