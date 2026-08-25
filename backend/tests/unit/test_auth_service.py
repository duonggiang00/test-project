from dataclasses import dataclass

from app.schemas.user import ForgotPasswordRequest
from app.services.auth_service import AuthService


@dataclass
class CapturingDelivery:
    email: str | None = None
    reset_link: str | None = None

    def deliver(self, *, email: str, reset_link: str) -> None:
        self.email = email
        self.reset_link = reset_link


class ScalarSession:
    def __init__(self, result: object | None) -> None:
        self.result = result

    def scalar(self, statement: object) -> object | None:
        del statement
        return self.result


def test_forgot_password_delivers_secret_only_through_boundary(capsys) -> None:
    user = type("UserRecord", (), {"email": "student@example.com"})()
    delivery = CapturingDelivery()

    response = AuthService.forgot_password(
        ScalarSession(user),  # type: ignore[arg-type]
        ForgotPasswordRequest(email=user.email),
        delivery,
    )

    assert response == {"message": "If the email exists, a reset link has been sent."}
    assert delivery.email == user.email
    assert delivery.reset_link is not None
    assert delivery.reset_link.startswith("http://localhost:3000/reset-password?token=")
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_forgot_password_does_not_reveal_missing_account(capsys) -> None:
    delivery = CapturingDelivery()

    response = AuthService.forgot_password(
        ScalarSession(None),  # type: ignore[arg-type]
        ForgotPasswordRequest(email="missing@example.com"),
        delivery,
    )

    assert response == {"message": "If the email exists, a reset link has been sent."}
    assert delivery.email is None
    assert delivery.reset_link is None
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
