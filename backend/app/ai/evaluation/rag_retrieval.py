"""Deterministic, content-free evaluation of RAG retrieval observations."""

from __future__ import annotations

import json
import hashlib
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.evaluation.dataset import GoldenDatasetCase
from app.ai.provider import EmbeddingProvider
from app.services.rag_retrieval_service import RagRetrievalService


class RetrievalEvaluationError(ValueError):
    """A safe evaluation error that never includes source content."""


class RetrievalObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    case_id: str = Field(min_length=1, max_length=80)
    mode: Literal["lexical", "hybrid"]
    retrieved_source_ids: list[str] = Field(max_length=50)
    query_count: int = Field(ge=0)
    latency_ms: float = Field(ge=0)


class RetrievalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    mode: Literal["lexical", "hybrid"]
    case_count: int = Field(ge=0)
    hit_rate_at_k: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    source_coverage: float = Field(ge=0, le=1)
    mean_latency_ms: float | None = Field(default=None, ge=0)
    p95_latency_ms: float | None = Field(default=None, ge=0)
    mean_query_count: float | None = Field(default=None, ge=0)


class RetrievalGateAssessment(BaseModel):
    """Sanitized activation and execution-gate result for one retrieval mode."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    mode: Literal["lexical", "hybrid"]
    activation_eligible: bool
    quality_gate_enforced: bool
    quality_thresholds_met: bool
    query_budget_met: bool
    evaluation_gate_passed: bool


@dataclass(frozen=True)
class RetrievalResult:
    source_ids: Sequence[str]
    query_count: int


class RetrievalServiceCase(BaseModel):
    """Sanitized case manifest for evaluating the production retrieval service."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    case_id: str = Field(min_length=1, max_length=80)
    material_id: UUID
    query: str = Field(min_length=1, max_length=20_000)
    required_source_ids: list[str] = Field(max_length=50)
    source_chunk_ids: dict[str, UUID] = Field(max_length=50)
    source_content_sha256: dict[str, str] = Field(max_length=50)

    @model_validator(mode="after")
    def validate_source_mapping(self) -> "RetrievalServiceCase":
        if set(self.required_source_ids) - set(self.source_chunk_ids):
            raise ValueError("required sources must have chunk mappings")
        if set(self.source_chunk_ids) != set(self.source_content_sha256):
            raise ValueError("every mapped source must have a content hash")
        if any(
            len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
            for value in self.source_content_sha256.values()
        ):
            raise ValueError("source content hashes must be lowercase SHA-256")
        if len(set(self.source_chunk_ids.values())) != len(self.source_chunk_ids):
            raise ValueError("source chunk mappings must be unique")
        return self


APPROVED_RETRIEVAL_POLICY_FINGERPRINT = (
    "4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51"
)
APPROVED_MIN_HIT_RATE = 1.0
APPROVED_MIN_SOURCE_COVERAGE = 1.0
APPROVED_MAX_QUERY_COUNT = 2


class _CountingSession:
    def __init__(self, db: object) -> None:
        self._db = db
        self.scalar_query_count = 0

    def scalars(self, statement: object):
        self.scalar_query_count += 1
        return self._db.scalars(statement)  # type: ignore[attr-defined]


RetrievalFn = Callable[[GoldenDatasetCase, Literal["lexical", "hybrid"]], RetrievalResult]


def evaluate_retrieval(
    cases: Sequence[GoldenDatasetCase],
    *,
    mode: Literal["lexical", "hybrid"],
    retrieve: RetrievalFn,
) -> tuple[RetrievalMetrics, list[RetrievalObservation]]:
    """Evaluate approved RAG cases while retaining identifiers only."""
    observations: list[RetrievalObservation] = []
    for case in sorted(
        (item for item in cases if item.use_case == "rag_chat"),
        key=lambda item: item.case_id,
    ):
        started = time.monotonic()
        result = retrieve(case, mode)
        elapsed_ms = (time.monotonic() - started) * 1000
        source_ids = list(result.source_ids)
        if len(source_ids) != len(set(source_ids)):
            raise RetrievalEvaluationError("retrieval returned duplicate source IDs")
        observations.append(
            RetrievalObservation(
                case_id=case.case_id,
                mode=mode,
                retrieved_source_ids=source_ids,
                query_count=result.query_count,
                latency_ms=elapsed_ms,
            )
        )

    required_by_case = {
        case.case_id: set(case.required_source_ids)
        for case in cases
        if case.use_case == "rag_chat"
    }
    hits = []
    reciprocal_ranks = []
    coverage = []
    for observation in observations:
        required = required_by_case[observation.case_id]
        retrieved = observation.retrieved_source_ids
        positions = [index for index, source_id in enumerate(retrieved, start=1) if source_id in required]
        hits.append(bool(positions))
        reciprocal_ranks.append(1 / positions[0] if positions else 0.0)
        coverage.append(len(set(retrieved) & required) / len(required) if required else 1.0)

    latencies = sorted(item.latency_ms for item in observations)
    p95_index = max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1)) if latencies else 0
    return (
        RetrievalMetrics(
            mode=mode,
            case_count=len(observations),
            hit_rate_at_k=sum(hits) / len(hits) if hits else 0.0,
            mean_reciprocal_rank=sum(reciprocal_ranks) / len(reciprocal_ranks)
            if reciprocal_ranks
            else 0.0,
            source_coverage=sum(coverage) / len(coverage) if coverage else 0.0,
            mean_latency_ms=sum(latencies) / len(latencies) if latencies else None,
            p95_latency_ms=latencies[p95_index] if latencies else None,
            mean_query_count=sum(item.query_count for item in observations) / len(observations)
            if observations
            else None,
        ),
        observations,
    )


def evaluate_retrieval_service(
    db: object,
    cases: Sequence[RetrievalServiceCase],
    *,
    mode: Literal["lexical", "hybrid"],
    embedding_provider: EmbeddingProvider | None = None,
) -> tuple[RetrievalMetrics, list[RetrievalObservation]]:
    """Evaluate the production retrieval service with SQL query-count telemetry."""
    observations: list[RetrievalObservation] = []
    required_by_case = {case.case_id: set(case.required_source_ids) for case in cases}
    for case in sorted(cases, key=lambda item: item.case_id):
        counting_db = _CountingSession(db)
        started = time.monotonic()
        result = RagRetrievalService.retrieve(
            counting_db,  # type: ignore[arg-type]
            material_id=case.material_id,
            query=case.query,
            mode=mode,
            embedding_provider=embedding_provider,
        )
        chunk_to_source = {
            str(chunk_id): source_id for source_id, chunk_id in case.source_chunk_ids.items()
        }
        source_ids = [
            chunk_to_source.get(str(item.chunk.id), str(item.chunk.id))
            for item in result
            if item.chunk.id is not None
        ]
        for item in result:
            if item.chunk.id is None:
                continue
            source_id = chunk_to_source.get(str(item.chunk.id))
            if source_id is not None:
                actual_hash = hashlib.sha256(item.chunk.content.encode("utf-8")).hexdigest()
                if actual_hash != case.source_content_sha256[source_id]:
                    raise RetrievalEvaluationError("source chunk mapping failed content binding")
        if len(source_ids) != len(set(source_ids)):
            raise RetrievalEvaluationError("retrieval returned duplicate source IDs")
        observations.append(
            RetrievalObservation(
                case_id=case.case_id,
                mode=mode,
                retrieved_source_ids=source_ids,
                query_count=counting_db.scalar_query_count,
                latency_ms=(time.monotonic() - started) * 1000,
            )
        )

    hits: list[bool] = []
    reciprocal_ranks: list[float] = []
    coverage: list[float] = []
    for observation in observations:
        required = required_by_case[observation.case_id]
        positions = [
            index
            for index, source_id in enumerate(observation.retrieved_source_ids, start=1)
            if source_id in required
        ]
        hits.append(bool(positions))
        reciprocal_ranks.append(1 / positions[0] if positions else 0.0)
        coverage.append(
            len(set(observation.retrieved_source_ids) & required) / len(required)
            if required
            else 1.0
        )
    latencies = sorted(item.latency_ms for item in observations)
    p95_index = max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1)) if latencies else 0
    return (
        RetrievalMetrics(
            mode=mode,
            case_count=len(observations),
            hit_rate_at_k=sum(hits) / len(hits) if hits else 0.0,
            mean_reciprocal_rank=sum(reciprocal_ranks) / len(reciprocal_ranks)
            if reciprocal_ranks
            else 0.0,
            source_coverage=sum(coverage) / len(coverage) if coverage else 0.0,
            mean_latency_ms=sum(latencies) / len(latencies) if latencies else None,
            p95_latency_ms=latencies[p95_index] if latencies else None,
            mean_query_count=sum(item.query_count for item in observations) / len(observations)
            if observations
            else None,
        ),
        observations,
    )


def assess_retrieval_gate(
    metrics: RetrievalMetrics,
    observations: Sequence[RetrievalObservation],
) -> RetrievalGateAssessment:
    """Apply quality only to activation candidates and query budget to both modes."""
    if any(item.mode != metrics.mode for item in observations):
        raise RetrievalEvaluationError("retrieval observations have inconsistent modes")
    quality_thresholds_met = (
        metrics.hit_rate_at_k >= APPROVED_MIN_HIT_RATE
        and metrics.source_coverage >= APPROVED_MIN_SOURCE_COVERAGE
    )
    query_budget_met = all(
        item.query_count <= APPROVED_MAX_QUERY_COUNT for item in observations
    )
    quality_gate_enforced = metrics.mode == "hybrid"
    evaluation_gate_passed = query_budget_met and (
        quality_thresholds_met or not quality_gate_enforced
    )
    return RetrievalGateAssessment(
        mode=metrics.mode,
        activation_eligible=quality_gate_enforced and evaluation_gate_passed,
        quality_gate_enforced=quality_gate_enforced,
        quality_thresholds_met=quality_thresholds_met,
        query_budget_met=query_budget_met,
        evaluation_gate_passed=evaluation_gate_passed,
    )


def write_retrieval_report(
    path: Path,
    metrics: RetrievalMetrics,
    observations: Sequence[RetrievalObservation],
    *,
    dataset_fingerprint: str | None = None,
    thresholds: dict[str, float | int] | None = None,
    gate: RetrievalGateAssessment | None = None,
) -> None:
    """Create a sanitized report once; never overwrite prior evidence."""
    payload = {
        "metrics": metrics.model_dump(mode="json"),
        "observations": [item.model_dump(mode="json") for item in observations],
    }
    if dataset_fingerprint is not None:
        payload["dataset_fingerprint"] = dataset_fingerprint
    if thresholds is not None:
        payload["thresholds"] = thresholds
    if gate is not None:
        payload["gate"] = gate.model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RetrievalEvaluationError("retrieval report already exists") from None
    try:
        with os.fdopen(fd, "wb") as report:
            report.write(serialized)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
