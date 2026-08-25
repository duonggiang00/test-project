from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from threading import Barrier
import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import AppException
from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.services.auth_session_service import AuthSessionService


def _register(client, *, email: str, password: str = "testpassword") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Session User", "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _login(client, *, email: str, password: str = "testpassword", remember: bool = False):
    response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
            "remember_me": str(remember).lower(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
def test_login_refresh_rotation_and_replay_revocation(client, db) -> None:
    email = f"rotation-{uuid.uuid4()}@example.com"
    user_data = _register(client, email=email)
    login = _login(client, email=email)
    assert login["access_expires_in"] == 900
    assert login["refresh_expires_in"] == 7 * 24 * 60 * 60

    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert rotated.status_code == 200, rotated.text
    replacement = rotated.json()
    assert replacement["refresh_token"] != login["refresh_token"]

    race = client.post(
        "/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert race.status_code == 401
    assert race.json()["error_code"] == "REFRESH_TOKEN_ALREADY_ROTATED"

    original = db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash
            == hashlib.sha256(login["refresh_token"].encode("utf-8")).hexdigest()
        )
    )
    assert original is not None
    original.rotated_at = datetime.now(timezone.utc) - timedelta(seconds=6)
    db.commit()

    replay = client.post(
        "/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert replay.status_code == 401
    assert replay.json()["error_code"] == "REFRESH_TOKEN_REPLAYED"
    revoked_replacement = client.post(
        "/auth/refresh",
        json={"refresh_token": replacement["refresh_token"]},
    )
    assert revoked_replacement.status_code == 401
    assert revoked_replacement.json()["error_code"] == "REFRESH_TOKEN_REVOKED"

    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_id == user_data["id"],
            AuditEvent.action == "auth.sessions_revoked",
        )
    ).all()
    assert any(event.event_metadata["reason"] == "refresh_replay" for event in events)
    serialized = "".join(str(event.event_metadata) for event in events)
    assert login["refresh_token"] not in serialized
    assert replacement["refresh_token"] not in serialized


@pytest.mark.integration
def test_logout_and_password_change_revoke_sessions(client) -> None:
    email = f"logout-{uuid.uuid4()}@example.com"
    _register(client, email=email)
    first = _login(client, email=email)
    second = _login(client, email=email)

    logout = client.post(
        "/auth/logout",
        json={"refresh_token": first["refresh_token"]},
    )
    assert logout.status_code == 200
    assert client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    ).status_code == 401
    assert client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    ).status_code == 200

    changed = client.put(
        "/auth/me/password",
        headers={"Authorization": f"Bearer {second['access_token']}"},
        json={"old_password": "testpassword", "new_password": "newpassword"},
    )
    assert changed.status_code == 200, changed.text
    assert client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    ).status_code == 401


@pytest.mark.integration
def test_concurrent_refresh_rotates_once_without_revoking_family(client) -> None:
    email = f"refresh-race-{uuid.uuid4()}@example.com"
    _register(client, email=email)
    login = _login(client, email=email)
    barrier = Barrier(2)

    def rotate_once() -> tuple[str, str | None]:
        with SessionLocal() as session:
            barrier.wait()
            try:
                tokens = AuthSessionService.refresh(session, login["refresh_token"])
                return "success", str(tokens["refresh_token"])
            except AppException as exc:
                session.rollback()
                return exc.error_code, None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: rotate_once(), range(2)))

    statuses = sorted(status for status, _ in results)
    assert statuses == ["REFRESH_TOKEN_ALREADY_ROTATED", "success"]
    replacement = next(token for status, token in results if status == "success")
    assert replacement is not None
    with SessionLocal() as session:
        rotated_again = AuthSessionService.refresh(session, replacement)
    assert rotated_again["refresh_token"] != replacement


@pytest.mark.integration
def test_logout_all_revokes_each_device_family(client) -> None:
    email = f"logout-all-{uuid.uuid4()}@example.com"
    _register(client, email=email)
    first = _login(client, email=email)
    second = _login(client, email=email, remember=True)
    assert second["refresh_expires_in"] == 30 * 24 * 60 * 60

    response = client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert response.status_code == 200, response.text
    for token in (first["access_token"], second["access_token"]):
        assert client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code == 401


@pytest.mark.integration
def test_inactive_user_cannot_login_or_refresh(client, db) -> None:
    email = f"inactive-{uuid.uuid4()}@example.com"
    registered = _register(client, email=email)
    login = _login(client, email=email)
    user = db.get(User, uuid.UUID(registered["id"]))
    assert user is not None
    user.is_active = False
    db.commit()

    denied_login = client.post(
        "/auth/login",
        data={"username": email, "password": "testpassword"},
    )
    assert denied_login.status_code == 403
    assert denied_login.json()["error_code"] == "ACCOUNT_DISABLED"
    denied_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert denied_refresh.status_code == 401
    assert denied_refresh.json()["error_code"] == "ACCOUNT_DISABLED"


@pytest.mark.integration
def test_concurrent_duplicate_registration_returns_one_conflict() -> None:
    email = f"concurrent-{uuid.uuid4()}@example.com"
    payload = UserCreate(
        email=email,
        full_name="Concurrent User",
        password="testpassword",
    )

    def register_once() -> int:
        with SessionLocal() as session:
            try:
                AuthService.register(session, payload)
                return 200
            except AppException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(lambda _: register_once(), range(2)))

    assert statuses == [200, 409]
