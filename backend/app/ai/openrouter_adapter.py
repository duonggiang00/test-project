"""The only module allowed to import the `openai` SDK (AI-001).

`material_service.py` used to own a module-level synchronous `OpenAI`
client and `ai_studio_service.py` a separate module-level `AsyncOpenAI`
client, both pointed at the same OpenRouter-compatible endpoint with the
same hardcoded model. This adapter unifies both into one class implementing
`app.ai.provider.AIProvider`: `generate` preserves the synchronous
non-streaming semantics `material_service.py` needs, `stream` preserves the
async streaming semantics `ai_studio_service.py` needs. Base URL, retry
behavior, and wire format are unchanged from before.

`backend.provider-sdk-import` (`scripts/architecture-guard.mjs`) fails the
build if any other module imports `openai`.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal, cast

import httpx
from openai import AsyncOpenAI, OpenAI

from app.ai.provider import (
    AIProviderError,
    EmbeddingRequest,
    EmbeddingResult,
    GenerateRequest,
    GenerateResult,
    ProviderExecutionBinding,
    StreamChunk,
    ToolCall,
    ToolCallDelta,
    TokenUsage,
)
from app.core.config import settings
from app.core.security_guardrails import sanitize_error

PROVIDER_NAME = "openrouter"
BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class OpenRouterRoutingPolicy:
    """Provider-specific routing constraints configured at the adapter edge."""

    only: tuple[str, ...]
    allow_fallbacks: bool
    require_parameters: bool
    data_collection: Literal["allow", "deny"]

    def request_body(self) -> dict[str, object]:
        return {
            "only": list(self.only),
            "allow_fallbacks": self.allow_fallbacks,
            "require_parameters": self.require_parameters,
            "data_collection": self.data_collection,
        }


class OpenRouterAdapter:
    """OpenRouter-backed implementation of `AIProvider`."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        sync_http_client: httpx.Client | None = None,
        async_http_client: httpx.AsyncClient | None = None,
        max_retries: int = 2,
        routing_policy: OpenRouterRoutingPolicy | None = None,
    ) -> None:
        resolved_key = api_key or getattr(settings, "OPENROUTER_API_KEY", None) or "mock_key"
        self._sync_client = OpenAI(
            base_url=BASE_URL,
            api_key=resolved_key,
            http_client=sync_http_client,
            max_retries=max_retries,
        )
        self._async_client = AsyncOpenAI(
            base_url=BASE_URL,
            api_key=resolved_key,
            http_client=async_http_client,
            max_retries=max_retries,
        )
        self._routing_policy = routing_policy
        self._max_retries = max_retries

    @property
    def execution_binding(self) -> ProviderExecutionBinding:
        """Attest the effective retry and provider-routing configuration."""
        routing_sha256 = None
        if self._routing_policy is not None:
            routing_sha256 = hashlib.sha256(
                json.dumps(
                    self._routing_policy.request_body(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
        return ProviderExecutionBinding(
            max_retries=self._max_retries,
            routing_policy_sha256=routing_sha256,
        )

    def generate(self, request: GenerateRequest) -> GenerateResult:
        """Run one non-streaming completion (used by material generation)."""
        started = time.monotonic()
        try:
            optional_arguments: dict[str, Any] = {}
            if request.temperature is not None:
                optional_arguments["temperature"] = request.temperature
            if request.max_tokens is not None:
                optional_arguments["max_tokens"] = request.max_tokens
            if request.response_format is not None:
                optional_arguments["response_format"] = {
                    "type": request.response_format
                }
            if self._routing_policy is not None:
                optional_arguments["extra_body"] = {
                    "provider": self._routing_policy.request_body()
                }
            response = self._sync_client.chat.completions.create(
                model=request.model,
                messages=cast(Any, request.messages),
                **optional_arguments,
            )
            latency_ms = (time.monotonic() - started) * 1000

            choice = response.choices[0]
            message = choice.message
            tool_calls = None
            message_tool_calls = getattr(message, "tool_calls", None) or []
            if message_tool_calls:
                tool_calls = [
                    ToolCall(
                        id=tc.id,
                        name=getattr(getattr(tc, "function", None), "name", None),
                        arguments=getattr(
                            getattr(tc, "function", None), "arguments", None
                        ),
                    )
                    for tc in message_tool_calls
                ]
            usage = getattr(response, "usage", None)
            return GenerateResult(
                text=message.content,
                tool_calls=tool_calls,
                provider=PROVIDER_NAME,
                model=response.model,
                usage=TokenUsage(
                    input_tokens=getattr(usage, "prompt_tokens", None),
                    output_tokens=getattr(usage, "completion_tokens", None),
                ),
                latency_ms=latency_ms,
                finish_reason=getattr(choice, "finish_reason", None),
                provider_variant=getattr(response, "provider", None),
            )
        except Exception as exc:
            raise AIProviderError(sanitize_error(exc)) from exc

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Create one validated embedding per input through OpenRouter."""
        if not request.inputs or any(not value.strip() for value in request.inputs):
            raise AIProviderError("AI_OUTPUT_INVALID")

        started = time.monotonic()
        try:
            extra_body: dict[str, object] = {"input_type": request.input_type}
            if self._routing_policy is not None:
                extra_body["provider"] = self._routing_policy.request_body()
            response = self._sync_client.embeddings.create(
                model=request.model,
                input=list(request.inputs),
                dimensions=request.dimensions,
                encoding_format="float",
                extra_body=extra_body,
            )
        except Exception as exc:
            raise AIProviderError(sanitize_error(exc)) from exc

        indices = [item.index for item in response.data]
        expected_indices = list(range(len(request.inputs)))
        if sorted(indices) != expected_indices or len(set(indices)) != len(indices):
            raise AIProviderError("AI_OUTPUT_INVALID")
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered]
        if (
            len(vectors) != len(request.inputs)
            or response.model != request.model
            or any(len(vector) != request.dimensions for vector in vectors)
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for vector in vectors
                for value in vector
            )
        ):
            raise AIProviderError("AI_OUTPUT_INVALID")

        usage = getattr(response, "usage", None)
        return EmbeddingResult(
            embeddings=[[float(value) for value in vector] for vector in vectors],
            provider=PROVIDER_NAME,
            model=response.model,
            input_tokens=getattr(usage, "prompt_tokens", None),
            latency_ms=(time.monotonic() - started) * 1000,
        )

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Run one streaming completion (used by the AI Studio chat endpoint)."""
        try:
            optional_arguments: dict[str, Any] = {}
            if request.response_format is not None:
                optional_arguments["response_format"] = {
                    "type": request.response_format
                }
            if self._routing_policy is not None:
                optional_arguments["extra_body"] = {
                    "provider": self._routing_policy.request_body()
                }
            response: Any = await self._async_client.chat.completions.create(
                model=request.model,
                messages=cast(Any, request.messages),
                tools=cast(Any, request.tools),
                stream=True,
                max_tokens=request.max_tokens,
                **optional_arguments,
            )
        except Exception as exc:
            raise AIProviderError(sanitize_error(exc)) from exc

        try:
            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                tool_call_deltas = None
                if delta.tool_calls:
                    tool_call_deltas = [
                        ToolCallDelta(
                            index=tc.index,
                            id=tc.id,
                            name=tc.function.name if tc.function else None,
                            arguments=tc.function.arguments if tc.function else None,
                        )
                        for tc in delta.tool_calls
                    ]
                yield StreamChunk(text=delta.content, tool_call_deltas=tool_call_deltas)
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(sanitize_error(exc)) from exc
