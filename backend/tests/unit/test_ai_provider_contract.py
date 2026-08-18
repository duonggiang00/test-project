"""Contract tests for `OpenRouterAdapter` (AI-001).

Every case mocks the httpx transport underneath the `openai` SDK client --
not the SDK client object itself -- so these tests actually exercise the
adapter's request construction and response/error parsing, with no real
network call.
"""
import httpx
import pytest

from app.ai.openrouter_adapter import OpenRouterAdapter
from app.ai.provider import AIProviderError, GenerateRequest


def _adapter(sync_handler=None, async_handler=None) -> OpenRouterAdapter:
    sync_client = (
        httpx.Client(transport=httpx.MockTransport(sync_handler))
        if sync_handler is not None
        else None
    )
    async_client = (
        httpx.AsyncClient(transport=httpx.MockTransport(async_handler))
        if async_handler is not None
        else None
    )
    return OpenRouterAdapter(
        api_key="test-key",
        sync_http_client=sync_client,
        async_http_client=async_client,
    )


def _completion_body(**overrides):
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "meta-llama/llama-3.1-8b-instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello world"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    body.update(overrides)
    return body


@pytest.mark.unit
def test_generate_returns_typed_text_provider_model_usage_and_latency():
    def handler(request):
        return httpx.Response(200, json=_completion_body())

    adapter = _adapter(sync_handler=handler)

    result = adapter.generate(
        GenerateRequest(
            messages=[{"role": "user", "content": "hi"}],
            model="meta-llama/llama-3.1-8b-instruct",
        )
    )

    assert result.text == "hello world"
    assert result.provider == "openrouter"
    assert result.model == "meta-llama/llama-3.1-8b-instruct"
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.finish_reason == "stop"
    assert result.latency_ms >= 0
    assert result.tool_calls is None


@pytest.mark.unit
def test_generate_parses_tool_calls_from_a_non_streaming_response():
    def handler(request):
        return httpx.Response(
            200,
            json=_completion_body(
                choices=[
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "draft_exam",
                                        "arguments": '{"title": "Quiz"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            ),
        )

    adapter = _adapter(sync_handler=handler)

    result = adapter.generate(
        GenerateRequest(
            messages=[{"role": "user", "content": "make an exam"}],
            model="meta-llama/llama-3.1-8b-instruct",
        )
    )

    assert result.text is None
    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert call.id == "call_1"
    assert call.name == "draft_exam"
    assert call.arguments == '{"title": "Quiz"}'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_yields_text_and_tool_call_deltas_matching_the_wire_shape():
    sse_body = (
        'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m",'
        '"choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}\n\n'
        'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m",'
        '"choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n'
        'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m",'
        '"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function",'
        '"function":{"name":"draft_exam","arguments":"{\\"a\\":1}"}}]},"finish_reason":null}]}\n\n'
        'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m",'
        '"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request):
        return httpx.Response(
            200, content=sse_body.encode(), headers={"content-type": "text/event-stream"}
        )

    adapter = _adapter(async_handler=handler)

    chunks = [
        chunk
        async for chunk in adapter.stream(
            GenerateRequest(
                messages=[{"role": "user", "content": "hi"}],
                model="m",
                tools=[{"type": "function", "function": {"name": "draft_exam"}}],
            )
        )
    ]

    assert [c.text for c in chunks] == ["", "Hello", None, None]
    assert chunks[2].tool_call_deltas is not None
    delta = chunks[2].tool_call_deltas[0]
    assert delta.index == 0
    assert delta.id == "call_1"
    assert delta.name == "draft_exam"
    assert delta.arguments == '{"a":1}'
    assert chunks[0].tool_call_deltas is None
    assert chunks[3].tool_call_deltas is None


@pytest.mark.unit
def test_generate_raises_provider_error_with_no_raw_text_on_malformed_response():
    def handler(request):
        return httpx.Response(
            200, content=b"not-json{{{", headers={"content-type": "application/json"}
        )

    adapter = _adapter(sync_handler=handler)

    with pytest.raises(AIProviderError) as excinfo:
        adapter.generate(
            GenerateRequest(
                messages=[{"role": "user", "content": "hi"}],
                model="m",
            )
        )

    # Sanitized error codes are a fixed, known vocabulary -- never the raw
    # provider/parser exception text.
    assert excinfo.value.error_code == "AI_INTERNAL_ERROR"


@pytest.mark.unit
def test_generate_raises_provider_error_on_timeout():
    def handler(request):
        raise httpx.TimeoutException("timed out")

    adapter = _adapter(sync_handler=handler)

    with pytest.raises(AIProviderError) as excinfo:
        adapter.generate(
            GenerateRequest(
                messages=[{"role": "user", "content": "hi"}],
                model="m",
            )
        )

    # `sanitize_error` (pre-existing, unchanged by AI-001) matches the literal
    # substring "timeout"; the SDK's timeout message is "Request timed out."
    # (no contiguous "timeout"), so it falls through to the generic sanitized
    # code. The adapter must not invent a more specific code that
    # `sanitize_error` itself would not produce.
    assert excinfo.value.error_code == "AI_INTERNAL_ERROR"


@pytest.mark.unit
def test_generate_raises_provider_error_on_rate_limit():
    def handler(request):
        return httpx.Response(
            429,
            json={"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
        )

    adapter = _adapter(sync_handler=handler)

    with pytest.raises(AIProviderError) as excinfo:
        adapter.generate(
            GenerateRequest(
                messages=[{"role": "user", "content": "hi"}],
                model="m",
            )
        )

    assert excinfo.value.error_code == "AI_RATE_LIMIT_EXCEEDED"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_raises_provider_error_on_timeout():
    def handler(request):
        raise httpx.TimeoutException("timed out")

    adapter = _adapter(async_handler=handler)

    with pytest.raises(AIProviderError) as excinfo:
        async for _ in adapter.stream(
            GenerateRequest(messages=[{"role": "user", "content": "hi"}], model="m")
        ):
            pass

    # `sanitize_error` (pre-existing, unchanged by AI-001) matches the literal
    # substring "timeout"; the SDK's timeout message is "Request timed out."
    # (no contiguous "timeout"), so it falls through to the generic sanitized
    # code. The adapter must not invent a more specific code that
    # `sanitize_error` itself would not produce.
    assert excinfo.value.error_code == "AI_INTERNAL_ERROR"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_raises_provider_error_on_rate_limit():
    def handler(request):
        return httpx.Response(
            429,
            json={"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
        )

    adapter = _adapter(async_handler=handler)

    with pytest.raises(AIProviderError) as excinfo:
        async for _ in adapter.stream(
            GenerateRequest(messages=[{"role": "user", "content": "hi"}], model="m")
        ):
            pass

    assert excinfo.value.error_code == "AI_RATE_LIMIT_EXCEEDED"
