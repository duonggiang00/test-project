"""Contract tests for `OpenRouterAdapter` (AI-001).

Every case mocks the httpx transport underneath the `openai` SDK client --
not the SDK client object itself -- so these tests actually exercise the
adapter's request construction and response/error parsing, with no real
network call.
"""
import json

import httpx
import pytest

from app.ai.openrouter_adapter import OpenRouterAdapter, OpenRouterRoutingPolicy
from app.ai.evaluation.live_baseline import V2_ROUTING_POLICY_SHA256
from app.ai.provider import AIProviderError, EmbeddingRequest, GenerateRequest


def _adapter(
    sync_handler=None,
    async_handler=None,
    *,
    max_retries: int = 2,
    routing_policy: OpenRouterRoutingPolicy | None = None,
) -> OpenRouterAdapter:
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
        max_retries=max_retries,
        routing_policy=routing_policy,
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
    sent_body = {}

    def handler(request):
        sent_body.update(json.loads(request.content))
        return httpx.Response(200, json=_completion_body())

    adapter = _adapter(sync_handler=handler)

    result = adapter.generate(
        GenerateRequest(
            messages=[{"role": "user", "content": "hi"}],
            model="meta-llama/llama-3.1-8b-instruct",
            temperature=0.0,
            max_tokens=321,
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
    assert sent_body["temperature"] == 0.0
    assert sent_body["max_tokens"] == 321


@pytest.mark.unit
def test_generate_omits_optional_parameters_and_reports_the_response_model():
    sent_body = {}

    def handler(request):
        sent_body.update(json.loads(request.content))
        return httpx.Response(200, json=_completion_body(model="resolved/model-v2"))

    adapter = _adapter(sync_handler=handler)
    result = adapter.generate(
        GenerateRequest(
            messages=[{"role": "user", "content": "hi"}],
            model="requested/model-v1",
        )
    )

    assert "temperature" not in sent_body
    assert "max_tokens" not in sent_body
    assert "response_format" not in sent_body
    assert "provider" not in sent_body
    assert result.model == "resolved/model-v2"
    assert adapter.execution_binding.max_retries == 2
    assert adapter.execution_binding.routing_policy_sha256 is None


@pytest.mark.unit
def test_generate_maps_json_mode_and_exact_routing_policy() -> None:
    sent_body = {}

    def handler(request):
        sent_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=_completion_body(provider="DeepInfra"),
        )

    adapter = _adapter(
        sync_handler=handler,
        max_retries=0,
        routing_policy=OpenRouterRoutingPolicy(
            only=("deepinfra",),
            allow_fallbacks=False,
            require_parameters=True,
            data_collection="deny",
        ),
    )
    result = adapter.generate(
        GenerateRequest(
            messages=[{"role": "user", "content": "hi"}],
            model="meta-llama/llama-3.1-8b-instruct",
            response_format="json_object",
        )
    )

    assert sent_body["response_format"] == {"type": "json_object"}
    assert sent_body["provider"] == {
        "only": ["deepinfra"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
    }
    assert result.provider_variant == "DeepInfra"
    assert adapter.execution_binding.max_retries == 0
    assert (
        adapter.execution_binding.routing_policy_sha256
        == V2_ROUTING_POLICY_SHA256
    )


@pytest.mark.unit
def test_generate_with_retries_disabled_makes_one_http_attempt_and_sanitizes_failure():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, json={"error": {"message": "private-detail"}})

    adapter = _adapter(sync_handler=handler, max_retries=0)

    with pytest.raises(AIProviderError, match="AI_INTERNAL_ERROR"):
        adapter.generate(
            GenerateRequest(
                messages=[{"role": "user", "content": "hi"}],
                model="requested/model-v1",
            )
        )

    assert attempts == 1


@pytest.mark.unit
def test_generate_sanitizes_a_response_without_choices():
    def handler(request):
        return httpx.Response(200, json=_completion_body(choices=[]))

    with pytest.raises(AIProviderError, match="AI_INTERNAL_ERROR"):
        _adapter(sync_handler=handler).generate(
            GenerateRequest(
                messages=[{"role": "user", "content": "hi"}],
                model="requested/model-v1",
            )
        )


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
def test_embed_sends_exact_batch_policy_and_returns_typed_vectors():
    sent_body = {}

    def handler(request):
        sent_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "openai/text-embedding-3-small",
                "data": [
                    {"object": "embedding", "index": 1, "embedding": [0.3, 0.4]},
                    {"object": "embedding", "index": 0, "embedding": [0.1, 0.2]},
                ],
                "usage": {"prompt_tokens": 7, "total_tokens": 7},
            },
        )

    adapter = _adapter(
        sync_handler=handler,
        max_retries=0,
        routing_policy=OpenRouterRoutingPolicy(
            only=("openai",),
            allow_fallbacks=False,
            require_parameters=True,
            data_collection="deny",
        ),
    )
    result = adapter.embed(
        EmbeddingRequest(
            inputs=("first", "second"),
            model="openai/text-embedding-3-small",
            dimensions=2,
            input_type="search_document",
        )
    )

    assert sent_body == {
        "input": ["first", "second"],
        "model": "openai/text-embedding-3-small",
        "encoding_format": "float",
        "dimensions": 2,
        "input_type": "search_document",
        "provider": {
            "only": ["openai"],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
        },
    }
    assert result.embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert result.provider == "openrouter"
    assert result.model == "openai/text-embedding-3-small"
    assert result.input_tokens == 7
    assert result.latency_ms >= 0


@pytest.mark.unit
def test_embed_accepts_openrouter_normalized_model_name_and_retains_policy_id():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "text-embedding-3-small",
                "data": [
                    {"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}
                ],
            },
        )

    result = _adapter(sync_handler=handler, max_retries=0).embed(
        EmbeddingRequest(
            inputs=("query",),
            model="openai/text-embedding-3-small",
            dimensions=2,
            input_type="search_query",
        )
    )

    assert result.model == "openai/text-embedding-3-small"


@pytest.mark.unit
@pytest.mark.parametrize(
    "vectors",
    (
        [[0.1]],
        [[0.1, float("nan")]],
        [[0.1, 0.2], [0.3, 0.4]],
    ),
)
def test_embed_rejects_invalid_provider_vectors(vectors):
    def handler(request):
        return httpx.Response(
            200,
            content=json.dumps(
                {
                    "object": "list",
                    "model": "embedding-model",
                    "data": [
                        {"object": "embedding", "index": index, "embedding": vector}
                        for index, vector in enumerate(vectors)
                    ],
                    "usage": {"prompt_tokens": 1, "total_tokens": 1},
                },
                allow_nan=True,
            ).encode(),
            headers={"content-type": "application/json"},
        )

    with pytest.raises(AIProviderError, match="AI_OUTPUT_INVALID"):
        _adapter(sync_handler=handler, max_retries=0).embed(
            EmbeddingRequest(
                inputs=("query",),
                model="embedding-model",
                dimensions=2,
                input_type="search_query",
            )
        )


@pytest.mark.unit
def test_embed_rejects_unrelated_response_model():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "different-embedding-model",
                "data": [
                    {"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}
                ],
            },
        )

    with pytest.raises(AIProviderError, match="AI_OUTPUT_INVALID"):
        _adapter(sync_handler=handler, max_retries=0).embed(
            EmbeddingRequest(
                inputs=("query",),
                model="openai/text-embedding-3-small",
                dimensions=2,
                input_type="search_query",
            )
        )


@pytest.mark.unit
def test_embed_rejects_non_contiguous_provider_indexes():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "embedding-model",
                "data": [
                    {"object": "embedding", "index": 0, "embedding": [0.1, 0.2]},
                    {"object": "embedding", "index": 0, "embedding": [0.3, 0.4]},
                ],
            },
        )

    with pytest.raises(AIProviderError, match="AI_OUTPUT_INVALID"):
        _adapter(sync_handler=handler, max_retries=0).embed(
            EmbeddingRequest(
                inputs=("first", "second"),
                model="embedding-model",
                dimensions=2,
                input_type="search_document",
            )
        )

    with pytest.raises(AIProviderError, match="AI_OUTPUT_INVALID"):
        _adapter(sync_handler=handler, max_retries=0).embed(
            EmbeddingRequest(
                inputs=("query",),
                model="embedding-model",
                dimensions=2,
                input_type="search_query",
            )
        )


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
