import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import OAuth2PasswordBearer
from limits import parse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError
import pytest
from slowapi.errors import RateLimitExceeded
from slowapi.wrappers import Limit
from starlette.requests import Request

from app.core.correlation import CorrelationMiddleware, REQUEST_ID_HEADER
from app.core.error_handlers import install_error_handlers, rate_limit_exception_handler
from app.core.exceptions import AppException
from app.api.endpoints import materials as material_endpoints
from app.db.session import get_db
from app.main import app as production_app
from app.services.material_service import MaterialService


class Payload(BaseModel):
    count: int = Field(ge=1)


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=1)


class CustomValidationPayload(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def reject_value(cls, value: str) -> str:
        raise PydanticCustomError(
            "custom_rejection",
            "Rejected value",
            {"submitted_value": value, "min_length": 3},
        )


def build_app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(CorrelationMiddleware)
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    @app.get("/app-error")
    def app_error():
        raise AppException(
            status_code=409,
            error_code="STATE_CONFLICT",
            message="internal compatibility message",
            details={"state": "published"},
        )

    @app.get("/http-error")
    def http_error():
        raise HTTPException(status_code=404, detail="must not leak")

    @app.get("/app-auth")
    def app_auth_error():
        raise AppException(
            status_code=401,
            error_code="UNAUTHORIZED",
            headers={
                "WWW-Authenticate": "Bearer",
                "Set-Cookie": "session=canary-secret",
            },
        )

    @app.get("/http-auth")
    def http_auth_error():
        raise HTTPException(
            status_code=401,
            detail="must not leak",
            headers={
                "WWW-Authenticate": "Bearer",
                "Set-Cookie": "session=canary-secret",
                "X-Provider-Error": "canary-provider-error",
            },
        )

    @app.get("/oauth-protected")
    def oauth_protected(_token: str = Depends(oauth2_scheme)):
        return {"ok": True}

    @app.get("/unsafe-app-error/{case_name}")
    def unsafe_app_error(case_name: str):
        details_by_case: dict[str, dict[str, Any]] = {
            "password": {"password_confirmation": "canary-password"},
            "token": {"state": "Bearer canary-token"},
            "cookie": {"state": "cookie=canary-cookie"},
            "provider": {"provider_error": "canary-provider-error"},
            "path": {"state": "/srv/private/document.txt"},
            "plain-secret": {"state": "canary_unreviewed_content"},
            "non-json": {"state": object()},
            "unknown-code": {"state": "published"},
        }
        error_code = "UNKNOWN_DETAIL_ERROR" if case_name == "unknown-code" else (
            "STATE_CONFLICT"
        )
        raise AppException(
            status_code=409,
            error_code=error_code,
            details=details_by_case[case_name],
        )

    @app.get("/material-delete-conflict")
    def material_delete_conflict():
        raise AppException(
            status_code=409,
            error_code="MATERIAL_DELETE_REQUIRES_CASCADE",
            details={
                "require_cascade": True,
                "linked_counts": {
                    "questions": 2,
                    "flashcard_decks": 1,
                    "topic_briefs": 0,
                },
            },
        )

    @app.post("/validation")
    def validation(payload: Payload):
        return payload

    @app.post("/strict-validation")
    def strict_validation(payload: StrictPayload):
        return payload

    @app.post("/custom-validation")
    def custom_validation(payload: CustomValidationPayload):
        return payload

    @app.get("/unexpected")
    def unexpected():
        raise RuntimeError("secret database path C:\\private\\db")

    @app.get("/success")
    def success():
        return {"ok": True}

    return app


def assert_canonical_error(response, error_code: str):
    body = response.json()
    assert set(body) == {"error_code", "details", "request_id"}
    assert body["error_code"] == error_code
    assert isinstance(body["details"], dict)
    assert response.headers[REQUEST_ID_HEADER] == body["request_id"]


def test_success_and_app_error_propagate_the_same_valid_request_id():
    request_id = str(uuid.uuid4())
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        success = client.get("/success", headers={REQUEST_ID_HEADER: request_id})
        error = client.get("/app-error", headers={REQUEST_ID_HEADER: request_id})

    assert success.status_code == 200
    assert success.headers[REQUEST_ID_HEADER] == request_id
    assert_canonical_error(error, "STATE_CONFLICT")
    assert error.json()["request_id"] == request_id
    assert error.json()["details"] == {"state": "published"}
    assert "message" not in error.json()


def test_validation_http_and_unexpected_errors_are_sanitized():
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        validation = client.post("/validation", json={"count": 0})
        http_error = client.get("/http-error")
        missing_route = client.get("/missing-route")
        unexpected = client.get("/unexpected")

    assert_canonical_error(validation, "VALIDATION_ERROR")
    assert validation.json()["details"]["fields"][0]["path"] == "count"
    assert_canonical_error(http_error, "RESOURCE_NOT_FOUND")
    assert_canonical_error(missing_route, "RESOURCE_NOT_FOUND")
    assert_canonical_error(unexpected, "INTERNAL_ERROR")
    assert "secret" not in unexpected.text.casefold()
    assert "private" not in unexpected.text.casefold()


def test_app_error_details_are_allowlisted_and_fail_closed():
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        responses = [
            client.get(f"/unsafe-app-error/{case_name}")
            for case_name in (
                "password",
                "token",
                "cookie",
                "provider",
                "path",
                "plain-secret",
                "non-json",
                "unknown-code",
            )
        ]

    for response in responses:
        assert response.status_code == 409
        assert response.json()["details"] == {}
        assert "canary" not in response.text.casefold()
        assert "private" not in response.text.casefold()


def test_material_delete_conflict_keeps_only_reviewed_structured_details():
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        response = client.get("/material-delete-conflict")

    assert_canonical_error(response, "MATERIAL_DELETE_REQUIRES_CASCADE")
    assert response.json()["details"] == {
        "require_cascade": True,
        "linked_counts": {
            "questions": 2,
            "flashcard_decks": 1,
            "topic_briefs": 0,
        },
    }


def test_material_endpoint_maps_delete_conflict_to_app_exception(monkeypatch):
    monkeypatch.setattr(
        MaterialService,
        "delete_material",
        lambda **_kwargs: {
            "require_cascade": True,
            "linked_counts": {
                "questions": 2,
                "flashcard_decks": 1,
                "topic_briefs": 0,
            },
            "message": "legacy text must not cross the endpoint boundary",
        },
    )

    with pytest.raises(AppException) as raised:
        material_endpoints.delete_material(
            material_id=uuid.uuid4(),
            cascade=False,
            keep_assets=False,
            db=object(),
            current_user=object(),
        )

    assert raised.value.error_code == "MATERIAL_DELETE_REQUIRES_CASCADE"
    assert raised.value.status_code == 409
    assert raised.value.details == {
        "require_cascade": True,
        "linked_counts": {
            "questions": 2,
            "flashcard_decks": 1,
            "topic_briefs": 0,
        },
    }
    assert "message" not in raised.value.details


def test_custom_validation_context_does_not_echo_submitted_values():
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        response = client.post(
            "/custom-validation",
            json={"value": "canary-validation-secret"},
        )

    assert_canonical_error(response, "VALIDATION_ERROR")
    field = response.json()["details"]["fields"][0]
    assert field["context"] == {"min_length": 3}
    assert "canary" not in response.text.casefold()
    assert "submitted" not in response.text.casefold()


def test_validation_paths_do_not_reflect_keys_and_output_is_bounded():
    payload = {"count": 1}
    payload.update(
        {
            f"password=canary-secret-{index}": "ignored"
            for index in range(10_000)
        }
    )
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        response = client.post("/strict-validation", json=payload)

    assert_canonical_error(response, "VALIDATION_ERROR")
    fields = response.json()["details"]["fields"]
    assert 0 < len(fields) <= 50
    assert {field["path"] for field in fields} == {"field"}
    assert len(response.content) < 9 * 1024
    assert "canary" not in response.text.casefold()
    assert "password=" not in response.text.casefold()


def test_http_protocol_headers_are_preserved_but_other_headers_are_dropped():
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        app_401 = client.get("/app-auth")
        manual_401 = client.get("/http-auth")
        oauth_401 = client.get("/oauth-protected")
        method_not_allowed = client.post("/success")

    assert_canonical_error(app_401, "UNAUTHORIZED")
    assert app_401.headers["WWW-Authenticate"] == "Bearer"
    assert "set-cookie" not in app_401.headers
    assert "canary" not in app_401.text.casefold()

    assert_canonical_error(manual_401, "UNAUTHORIZED")
    assert manual_401.headers["WWW-Authenticate"] == "Bearer"
    assert "set-cookie" not in manual_401.headers
    assert "x-provider-error" not in manual_401.headers
    assert "canary" not in manual_401.text.casefold()

    assert_canonical_error(oauth_401, "UNAUTHORIZED")
    assert oauth_401.headers["WWW-Authenticate"] == "Bearer"

    assert_canonical_error(method_not_allowed, "METHOD_NOT_ALLOWED")
    assert method_not_allowed.headers["Allow"] == "GET"


def test_production_login_invalid_credentials_keep_bearer_challenge():
    class MissingUserQuery:
        def filter(self, *_args):
            return self

        def first(self):
            return None

    class MissingUserSession:
        def query(self, *_args):
            return MissingUserQuery()

    def override_get_db():
        yield MissingUserSession()

    production_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(
            production_app,
            raise_server_exceptions=False,
        ) as client:
            response = client.post(
                "/auth/login",
                data={
                    "username": "missing@example.test",
                    "password": "canary-password",
                },
            )
    finally:
        production_app.dependency_overrides.pop(get_db, None)

    assert_canonical_error(response, "INVALID_CREDENTIALS")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert "canary" not in response.text.casefold()


def test_invalid_request_ids_are_replaced_and_requests_do_not_share_ids():
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        first = client.get(
            "/app-error",
            headers={REQUEST_ID_HEADER: "invalid\trequest-id"},
        )
        second = client.get("/app-error")

    assert_canonical_error(first, "STATE_CONFLICT")
    assert_canonical_error(second, "STATE_CONFLICT")
    assert uuid.UUID(first.json()["request_id"])
    assert uuid.UUID(second.json()["request_id"])
    assert first.json()["request_id"] != second.json()["request_id"]


def test_rate_limit_handler_uses_the_canonical_envelope():
    request_id = str(uuid.uuid4())
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "state": {"request_id": request_id},
        }
    )
    exception = RateLimitExceeded(
        Limit(
            parse("1/minute"),
            lambda: "test-key",
            None,
            False,
            None,
            None,
            None,
            1,
            False,
        )
    )

    response = rate_limit_exception_handler(request, exception)

    assert response.status_code == 429
    assert response.headers[REQUEST_ID_HEADER] == request_id
    assert response.headers["Retry-After"] == "60"
    assert response.body == (
        '{"error_code":"RATE_LIMIT_EXCEEDED","details":{},'
        f'"request_id":"{request_id}"}}'
    ).encode()
