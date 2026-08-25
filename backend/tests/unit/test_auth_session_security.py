from datetime import datetime, timezone
from uuid import uuid4

from jose import jwt

from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token
from app.models.user import User
from app.services.auth_session_service import AuthSessionService


def user_record() -> User:
    return User(
        id=uuid4(),
        email="security@example.com",
        password_hash="unused",
        full_name="Security Test",
        role="student",
        is_active=True,
    )


def test_access_token_uses_short_ttl_and_session_claims() -> None:
    family_id = uuid4()
    before = datetime.now(timezone.utc).timestamp()
    encoded = create_access_token(
        user_record().id,
        session_family_id=family_id,
    )
    payload = jwt.decode(encoded, settings.SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["type"] == "access"
    assert payload["sid"] == str(family_id)
    assert payload["jti"]
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 - 2 <= payload["exp"] - before
    assert payload["exp"] - before <= settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 2


def test_refresh_secret_is_hashed_and_uses_normal_ttl() -> None:
    session, raw_token = AuthSessionService._new_refresh_session(
        user_record(),
        remember_me=False,
    )

    assert raw_token not in session.token_hash
    assert session.token_hash == AuthSessionService._hash_token(raw_token)
    assert len(session.token_hash) == 64
    assert (session.expires_at - session.created_at).days == 7


def test_remembered_refresh_session_uses_thirty_day_ttl() -> None:
    session, _ = AuthSessionService._new_refresh_session(
        user_record(),
        remember_me=True,
    )

    assert (session.expires_at - session.created_at).days == 30
