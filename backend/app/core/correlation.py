from contextvars import ContextVar
import re
import uuid

from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


REQUEST_ID_HEADER = "X-Request-ID"
# A ULID carries 128 bits in 26 Crockford Base32 characters. The first
# character therefore has only three significant bits and must be 0-7.
_ULID_PATTERN = re.compile(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$", re.IGNORECASE)
_current_request_id: ContextVar[str | None] = ContextVar(
    "current_request_id",
    default=None,
)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def canonicalize_request_id(candidate: str | None) -> str | None:
    if candidate:
        try:
            return str(uuid.UUID(candidate))
        except ValueError:
            if _ULID_PATTERN.fullmatch(candidate):
                return candidate.upper()
    return None


def normalize_request_id(candidate: str | None) -> str:
    return canonicalize_request_id(candidate) or new_correlation_id()


def get_current_request_id() -> str | None:
    return _current_request_id.get()


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if not isinstance(request_id, str):
        request_id = new_correlation_id()
        request.state.request_id = request_id
    return request_id


class CorrelationMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_request_id = headers.get(REQUEST_ID_HEADER.casefold().encode("ascii"))
        candidate = None
        if raw_request_id is not None:
            try:
                candidate = raw_request_id.decode("ascii")
            except UnicodeDecodeError:
                candidate = None
        request_id = normalize_request_id(candidate)
        scope.setdefault("state", {})["request_id"] = request_id
        token = _current_request_id.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            _current_request_id.reset(token)
