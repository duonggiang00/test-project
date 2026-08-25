from typing import Protocol
from threading import Lock

from app.core.config import settings


class PasswordResetDelivery(Protocol):
    """Boundary for delivering password-reset links outside application logs."""

    def deliver(self, *, email: str, reset_link: str) -> None: ...


class DisabledPasswordResetDelivery:
    """Safe default until a production delivery adapter is approved."""

    def deliver(self, *, email: str, reset_link: str) -> None:
        del email, reset_link


class InMemoryPasswordResetDelivery:
    """Explicit development outbox that never writes secrets to logs."""

    def __init__(self) -> None:
        self._links: dict[str, str] = {}
        self._lock = Lock()

    def deliver(self, *, email: str, reset_link: str) -> None:
        with self._lock:
            self._links[email] = reset_link

    def pop(self, email: str) -> str | None:
        with self._lock:
            return self._links.pop(email, None)


password_reset_delivery: PasswordResetDelivery = (
    InMemoryPasswordResetDelivery()
    if settings.ENV.casefold() == "development"
    else DisabledPasswordResetDelivery()
)
