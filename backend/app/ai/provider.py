"""Provider-neutral generation/streaming boundary (AI-001).

No service module may import a provider SDK directly (enforced by the
`backend.provider-sdk-import` architecture-guard rule). Instead, services
depend on the `AIProvider` protocol declared here and receive a concrete
adapter (currently `app.ai.openrouter_adapter.OpenRouterAdapter`) through a
default constructor parameter, mirroring `app.core.file_storage.FileStorage`.

Every provider call returns a typed result carrying usage/latency metadata
so a later phase (AI-003) can attach it to audit events, and every provider
failure is raised as `AIProviderError`, whose `error_code` is always a
pre-sanitized stable code (see `app.core.security_guardrails.sanitize_error`)
-- raw provider exception text must never reach a caller.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class TokenUsage:
    """Token accounting for one provider call, when the provider reports it."""

    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class ToolCall:
    """A complete tool/function call as returned by a non-streaming response."""

    id: str | None
    name: str | None
    arguments: str | None


@dataclass(frozen=True)
class ToolCallDelta:
    """One incremental tool-call fragment from a streamed response.

    Mirrors the OpenAI-compatible streaming delta shape exactly (index/id/
    name/arguments chunks that the caller accumulates) so existing callers
    keep their exact wire format.
    """

    index: int
    id: str | None
    name: str | None
    arguments: str | None


@dataclass(frozen=True)
class StreamChunk:
    """One event from `AIProvider.stream`.

    Both fields may be populated on the same chunk (matching the underlying
    SDK, which can deliver text and a tool-call fragment in one delta).
    """

    text: str | None = None
    tool_call_deltas: list[ToolCallDelta] | None = None


@dataclass(frozen=True)
class GenerateResult:
    """Typed result of a non-streaming `AIProvider.generate` call."""

    text: str | None
    tool_calls: list[ToolCall] | None
    provider: str
    model: str
    usage: TokenUsage
    latency_ms: float
    finish_reason: str | None = None
    provider_variant: str | None = None


@dataclass(frozen=True)
class GenerateRequest:
    """Typed input to `AIProvider.generate`/`AIProvider.stream`."""

    messages: list[dict[str, Any]]
    model: str
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: Literal["json_object"] | None = None


@dataclass(frozen=True)
class ProviderExecutionBinding:
    """Runtime-attested retry and routing policy for governed evaluations."""

    max_retries: int
    routing_policy_sha256: str | None = None


class AIProviderError(Exception):
    """Raised by an `AIProvider` on failure.

    `error_code` is always produced by `sanitize_error` on the underlying
    provider/transport exception -- never the raw exception text -- so it is
    safe for a caller to surface directly to a client or log verbatim.
    """

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


class AIProvider(Protocol):
    """Replaceable boundary for LLM generation and streaming."""

    @property
    def execution_binding(self) -> ProviderExecutionBinding:
        """Describe effective adapter policy without exposing credentials."""
        ...

    def generate(self, request: GenerateRequest) -> GenerateResult:
        """Run one non-streaming completion. Raises `AIProviderError`."""
        ...

    def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Run one streaming completion. Raises `AIProviderError`."""
        ...
