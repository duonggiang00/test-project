import logging
import json
import math
import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, get_args, get_origin

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.correlation import REQUEST_ID_HEADER, get_request_id
from app.core.exceptions import AppException
from app.core.safe_payload import UnsafeStructuredPayloadError, validate_safe_mapping


logger = logging.getLogger(__name__)

MAX_ERROR_DETAILS_BYTES = 8 * 1024
MAX_VALIDATION_FIELD_ERRORS = 50
MAX_VALIDATION_PATH_SEGMENTS = 6
_SAFE_PROTOCOL_HEADER_NAMES = frozenset(
    {"allow", "retry-after", "www-authenticate"}
)
_ALLOW_HEADER_PATTERN = re.compile(r"^[A-Z]+(?:,\s*[A-Z]+)*$")
_RETRY_AFTER_PATTERN = re.compile(r"^[0-9]{1,10}$")
_WWW_AUTHENTICATE_PATTERN = re.compile(
    r'^Bearer(?: realm="[A-Za-z0-9 ._-]{1,64}")?$'
)
_VALIDATION_RULE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_VALIDATION_PATH_SEGMENT_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"
)
_RESOURCE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MEDIA_TYPE_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}$"
)
_KNOWN_STATES = frozenset(
    {
        "active",
        "approved",
        "awaiting_review",
        "deleted",
        "draft",
        "failed",
        "generated",
        "inactive",
        "processing",
        "published",
        "rejected",
        "requested",
    }
)
_MATERIAL_LINK_COUNT_FIELDS = frozenset(
    {"flashcard_decks", "questions", "topic_briefs"}
)
_SAFE_VALIDATION_CONTEXT_KEYS = frozenset(
    {
        "decimal_places",
        "ge",
        "gt",
        "le",
        "lt",
        "max_digits",
        "max_length",
        "min_length",
        "multiple_of",
    }
)

# AppException details are deny-by-default. Adding structured context for a new
# error code requires an explicit reviewable policy entry here.
_ERROR_DETAIL_FIELDS = MappingProxyType(
    {
        "FILE_TOO_LARGE": frozenset({"max_bytes"}),
        "MATERIAL_DELETE_REQUIRES_CASCADE": frozenset(
            {"linked_counts", "require_cascade"}
        ),
        "RESOURCE_NOT_FOUND": frozenset({"resource"}),
        "STATE_CONFLICT": frozenset({"expected_state", "state"}),
        "UNSUPPORTED_MEDIA_TYPE": frozenset({"allowed_types"}),
    }
)


def _matches_error_detail_schema(
    error_code: str,
    details: dict[str, Any],
) -> bool:
    if not details:
        return True
    if error_code == "STATE_CONFLICT":
        return all(
            isinstance(value, str) and value in _KNOWN_STATES
            for value in details.values()
        )
    if error_code == "RESOURCE_NOT_FOUND":
        resource = details.get("resource")
        return isinstance(resource, str) and bool(
            _RESOURCE_NAME_PATTERN.fullmatch(resource)
        )
    if error_code == "FILE_TOO_LARGE":
        max_bytes = details.get("max_bytes")
        return type(max_bytes) is int and max_bytes > 0
    if error_code == "UNSUPPORTED_MEDIA_TYPE":
        allowed_types = details.get("allowed_types")
        return (
            isinstance(allowed_types, list)
            and bool(allowed_types)
            and all(
                isinstance(value, str) and _MEDIA_TYPE_PATTERN.fullmatch(value)
                for value in allowed_types
            )
        )
    if error_code == "MATERIAL_DELETE_REQUIRES_CASCADE":
        linked_counts = details.get("linked_counts")
        return (
            details.get("require_cascade") is True
            and isinstance(linked_counts, dict)
            and set(linked_counts) == _MATERIAL_LINK_COUNT_FIELDS
            and all(type(value) is int and value >= 0 for value in linked_counts.values())
        )
    return False


def _safe_app_error_details(exc: AppException) -> dict[str, Any]:
    allowed_fields = _ERROR_DETAIL_FIELDS.get(exc.error_code, frozenset())
    try:
        safe_details = validate_safe_mapping(
            exc.details,
            allowed_top_level_fields=allowed_fields,
            max_serialized_bytes=MAX_ERROR_DETAILS_BYTES,
            max_depth=6,
            max_collection_items=50,
        )
        return safe_details if _matches_error_detail_schema(
            exc.error_code,
            safe_details,
        ) else {}
    except UnsafeStructuredPayloadError:
        return {}


def _safe_protocol_headers(
    headers: Mapping[str, str] | None,
) -> dict[str, str]:
    safe_headers: dict[str, str] = {}
    for name, value in (headers or {}).items():
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        normalized_name = name.casefold()
        if normalized_name not in _SAFE_PROTOCOL_HEADER_NAMES:
            continue
        if normalized_name == "allow" and not _ALLOW_HEADER_PATTERN.fullmatch(value):
            continue
        if normalized_name == "retry-after" and not _RETRY_AFTER_PATTERN.fullmatch(
            value
        ):
            continue
        if normalized_name == "www-authenticate" and not (
            _WWW_AUTHENTICATE_PATTERN.fullmatch(value)
        ):
            continue
        safe_headers[name] = value
    return safe_headers


def _safe_validation_context(error: dict[str, Any]) -> dict[str, int | float]:
    safe_context: dict[str, int | float] = {}
    for key, value in (error.get("ctx") or {}).items():
        if key not in _SAFE_VALIDATION_CONTEXT_KEYS:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        safe_context[key] = value
    return safe_context


def _collect_model_field_names(
    annotation: object,
    field_names: set[str],
    seen_models: set[type[BaseModel]],
) -> None:
    origin = get_origin(annotation)
    if origin is not None:
        for argument in get_args(annotation):
            _collect_model_field_names(argument, field_names, seen_models)
        return
    if not isinstance(annotation, type) or not issubclass(annotation, BaseModel):
        return
    if annotation in seen_models:
        return
    seen_models.add(annotation)
    for name, model_field in annotation.model_fields.items():
        field_names.add(name)
        alias = model_field.alias
        if isinstance(alias, str):
            field_names.add(alias)
        _collect_model_field_names(
            model_field.annotation,
            field_names,
            seen_models,
        )


def _declared_validation_field_names(request: Request) -> frozenset[str]:
    route = request.scope.get("route")
    root_dependant = getattr(route, "dependant", None)
    if root_dependant is None:
        return frozenset()

    field_names: set[str] = set()
    seen_dependants: set[int] = set()
    seen_models: set[type[BaseModel]] = set()
    pending = [root_dependant]
    while pending:
        dependant = pending.pop()
        if id(dependant) in seen_dependants:
            continue
        seen_dependants.add(id(dependant))
        pending.extend(getattr(dependant, "dependencies", ()))
        for collection_name in (
            "body_params",
            "query_params",
            "path_params",
            "header_params",
            "cookie_params",
        ):
            for parameter in getattr(dependant, collection_name, ()):
                for candidate in (
                    getattr(parameter, "name", None),
                    getattr(parameter, "alias", None),
                ):
                    if isinstance(candidate, str):
                        field_names.add(candidate)
                annotation = getattr(
                    getattr(parameter, "field_info", None),
                    "annotation",
                    None,
                )
                _collect_model_field_names(
                    annotation,
                    field_names,
                    seen_models,
                )
    return frozenset(field_names)


def _safe_validation_path(
    error: dict[str, Any],
    *,
    declared_fields: frozenset[str],
) -> str:
    raw_location = error.get("loc", ())
    if not isinstance(raw_location, (tuple, list)):
        return "field"

    safe_parts: list[str] = []
    for part in raw_location[1 : 1 + MAX_VALIDATION_PATH_SEGMENTS]:
        if type(part) is int and part >= 0:
            safe_parts.append("item")
        elif (
            isinstance(part, str)
            and part in declared_fields
            and _VALIDATION_PATH_SEGMENT_PATTERN.fullmatch(part)
        ):
            safe_parts.append(part)
        else:
            # Mapping keys and extra-field names can be attacker-controlled.
            # Keep the path shape useful without reflecting their content.
            safe_parts.append("field")
    return ".".join(safe_parts) or "field"


def _fits_validation_details_limit(fields: list[dict[str, Any]]) -> bool:
    encoded = json.dumps(
        {"fields": fields},
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return len(encoded) <= MAX_ERROR_DETAILS_BYTES


def _response(
    request: Request,
    *,
    status_code: int,
    error_code: str,
    details: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    response_headers = _safe_protocol_headers(headers)
    response_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "details": details or {},
            "request_id": request_id,
        },
        headers=response_headers,
    )


def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppException):
        raise TypeError("app_exception_handler received an incompatible exception")
    return _response(
        request,
        status_code=exc.status_code,
        error_code=exc.error_code,
        details=_safe_app_error_details(exc),
        headers=exc.headers,
    )


def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise TypeError("validation handler received an incompatible exception")
    fields: list[dict[str, Any]] = []
    declared_fields = _declared_validation_field_names(request)
    for error in exc.errors()[:MAX_VALIDATION_FIELD_ERRORS]:
        rule = error.get("type", "invalid")
        if not isinstance(rule, str) or not _VALIDATION_RULE_PATTERN.fullmatch(rule):
            rule = "invalid"
        field = {
            "path": _safe_validation_path(
                error,
                declared_fields=declared_fields,
            ),
            "rule": rule,
            "context": _safe_validation_context(error),
        }
        if not _fits_validation_details_limit([*fields, field]):
            break
        fields.append(field)
    return _response(
        request,
        status_code=422,
        error_code="VALIDATION_ERROR",
        details={"fields": fields},
    )


_HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "STATE_CONFLICT",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "RATE_LIMIT_EXCEEDED",
}


def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise TypeError("HTTP handler received an incompatible exception")
    return _response(
        request,
        status_code=exc.status_code,
        error_code=_HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR"),
        headers=exc.headers,
    )


def rate_limit_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RateLimitExceeded):
        raise TypeError("rate-limit handler received an incompatible exception")
    retry_after = "1"
    if exc.limit is not None:
        retry_after = str(exc.limit.limit.get_expiry())
    return _response(
        request,
        status_code=429,
        error_code="RATE_LIMIT_EXCEEDED",
        headers={"Retry-After": retry_after},
    )


def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(
        "Unhandled application exception request_id=%s exception_type=%s",
        request_id,
        type(exc).__name__,
    )
    return _response(
        request,
        status_code=500,
        error_code="INTERNAL_ERROR",
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
