import json

from app.core.exceptions import AppException
from app.main import app, app_exception_handler


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
        None,
        AppException(
            status_code=409,
            error_code="STATE_CONFLICT",
            message="Conflict",
        ),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "error_code": "STATE_CONFLICT",
        "message": "Conflict",
    }
