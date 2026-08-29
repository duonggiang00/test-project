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

import time
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx
from openai import AsyncOpenAI, OpenAI

from app.ai.provider import (
    AIProviderError,
    GenerateRequest,
    GenerateResult,
    StreamChunk,
    ToolCall,
    ToolCallDelta,
    TokenUsage,
)
from app.core.config import settings
from app.core.security_guardrails import sanitize_error

PROVIDER_NAME = "openrouter"
BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterAdapter:
    """OpenRouter-backed implementation of `AIProvider`."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        sync_http_client: httpx.Client | None = None,
        async_http_client: httpx.AsyncClient | None = None,
        max_retries: int = 2,
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

    def generate(self, request: GenerateRequest) -> GenerateResult:
        """Run one non-streaming completion (used by material generation)."""
        started = time.monotonic()
        try:
            optional_arguments: dict[str, Any] = {}
            if request.temperature is not None:
                optional_arguments["temperature"] = request.temperature
            if request.max_tokens is not None:
                optional_arguments["max_tokens"] = request.max_tokens
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
            )
        except Exception as exc:
            raise AIProviderError(sanitize_error(exc)) from exc

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Run one streaming completion (used by the AI Studio chat endpoint)."""
        try:
            response: Any = await self._async_client.chat.completions.create(
                model=request.model,
                messages=cast(Any, request.messages),
                tools=cast(Any, request.tools),
                stream=True,
                max_tokens=request.max_tokens,
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
