import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.correlation import REQUEST_ID_HEADER
from app.core.exceptions import AppException
from starlette.requests import Request

from app.core.error_handlers import app_exception_handler
from app.main import app


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def api_operations(schema):
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method.casefold() in HTTP_METHODS:
                yield path, method.casefold(), operation


def test_openapi_operations_have_unique_ids_and_canonical_paths():
    schema = app.openapi()
    operations = list(api_operations(schema))

    assert operations
    assert all(path == "/" or not path.endswith("/") for path, _, _ in operations)

    operation_ids = [operation["operationId"] for _, _, operation in operations]
    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_operations_are_tagged_for_domain_discovery():
    operations = list(api_operations(app.openapi()))

    assert all(
        operation.get("tags")
        for path, _method, operation in operations
        if path != "/"
    )


def test_app_exception_uses_stable_machine_readable_envelope():
    response = app_exception_handler(
        Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [],
                "state": {"request_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"},
            }
        ),
        AppException(
            status_code=409,
            error_code="STATE_CONFLICT",
            message="Conflict",
            details={"state": "draft"},
        ),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "error_code": "STATE_CONFLICT",
        "details": {"state": "draft"},
        "request_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    }


def test_main_app_propagates_and_exposes_request_id_contract():
    request_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    origin = settings.cors_origins[0]
    with TestClient(app, raise_server_exceptions=False) as client:
        success = client.get(
            "/",
            headers={REQUEST_ID_HEADER: request_id, "Origin": origin},
        )
        missing = client.get(
            "/missing-route",
            headers={REQUEST_ID_HEADER: request_id, "Origin": origin},
        )

    assert success.headers[REQUEST_ID_HEADER] == request_id
    assert REQUEST_ID_HEADER.casefold() in success.headers[
        "access-control-expose-headers"
    ].casefold()
    assert missing.json() == {
        "error_code": "RESOURCE_NOT_FOUND",
        "details": {},
        "request_id": request_id,
    }
    assert missing.headers[REQUEST_ID_HEADER] == request_id
