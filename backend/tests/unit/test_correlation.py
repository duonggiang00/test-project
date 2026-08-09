import asyncio
import json
import uuid

import pytest

from app.core.correlation import (
    CorrelationMiddleware,
    REQUEST_ID_HEADER,
    get_current_request_id,
    normalize_request_id,
)


VALID_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_normalizes_only_uuid_or_crockford_ulid_request_ids():
    request_id = uuid.uuid4()

    assert normalize_request_id(str(request_id).upper()) == str(request_id)
    assert normalize_request_id(VALID_ULID.casefold()) == VALID_ULID

    for unsafe in (
        "",
        "not-a-correlation-id",
        "x" * 65,
        "request\nsmuggled",
        "01ARZ3NDEKTSV4RRFFQ69G5FAI",
        "Z0000000000000000000000000",
        "80000000000000000000000000",
    ):
        replacement = normalize_request_id(unsafe)
        assert replacement != unsafe
        assert uuid.UUID(replacement)


@pytest.mark.asyncio
async def test_asgi_middleware_isolates_concurrent_context_and_resets_it():
    async def echo_app(scope, receive, send):
        await asyncio.sleep(0)
        request_id = get_current_request_id()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps({"request_id": request_id}).encode(),
            }
        )

    middleware = CorrelationMiddleware(echo_app)

    async def invoke(request_id: str):
        sent = []
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [
                (REQUEST_ID_HEADER.casefold().encode("ascii"), request_id.encode())
            ],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "state": {},
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        await middleware(scope, receive, send)
        response_headers = dict(sent[0]["headers"])
        body = json.loads(sent[1]["body"])
        return scope["state"]["request_id"], response_headers, body

    first = str(uuid.uuid4())
    second = str(uuid.uuid4())
    results = await asyncio.gather(invoke(first), invoke(second))

    assert {result[0] for result in results} == {first, second}
    for state_id, headers, body in results:
        assert headers[REQUEST_ID_HEADER.casefold().encode("ascii")].decode() == state_id
        assert body == {"request_id": state_id}
    assert get_current_request_id() is None
