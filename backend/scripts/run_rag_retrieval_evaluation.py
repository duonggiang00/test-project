"""Run the approved RAG retrieval campaign in an isolated PostgreSQL database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid5

if __name__ == "__main__":
    os.environ["ENV"] = "test"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.ai.evaluation.dataset import (  # noqa: E402
    GoldenDataset,
    GoldenDatasetCase,
    contains_secret_like_content,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.rag_retrieval import (  # noqa: E402
    APPROVED_MAX_QUERY_COUNT,
    APPROVED_MIN_HIT_RATE,
    APPROVED_MIN_SOURCE_COVERAGE,
    APPROVED_RETRIEVAL_POLICY_FINGERPRINT,
    RetrievalEvaluationError,
    RetrievalGateAssessment,
    RetrievalServiceCase,
    assess_retrieval_gate,
    evaluate_retrieval_service,
    write_retrieval_report,
)
from app.ai.provider import (  # noqa: E402
    AIProviderError,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResult,
)
from app.ai.openrouter_adapter import (  # noqa: E402
    OpenRouterAdapter,
    OpenRouterRoutingPolicy,
)
from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.document_chunk import DocumentChunk  # noqa: E402
from app.models.material import StudyMaterial  # noqa: E402
from app.models.user import User  # noqa: E402
from scripts.test_database import build_manager  # noqa: E402


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.jsonl"
APPROVAL_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.approval.json"
REPORT_ROOT = BACKEND_ROOT / "reports" / "ai-evaluation" / "rag-semantic-001"
FIXTURE_NAMESPACE = UUID("89d62f9a-2850-48df-a535-22b78337583b")
RAG_CASE_COUNT = 16
DISTRACTOR_COUNT = 3
MAX_EMBEDDING_REQUESTS = 1 + RAG_CASE_COUNT
MAX_EMBEDDING_INPUTS = RAG_CASE_COUNT * (1 + DISTRACTOR_COUNT) + RAG_CASE_COUNT
RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")
EVALUATION_ROUTING_POLICY = OpenRouterRoutingPolicy(
    only=("openai",),
    allow_fallbacks=False,
    require_parameters=True,
    data_collection="deny",
)


@dataclass(frozen=True)
class FixtureChunk:
    chunk_id: UUID
    source_id: str
    content: str
    required: bool


@dataclass(frozen=True)
class FixtureCase:
    case_id: str
    material_id: UUID
    query: str
    chunks: tuple[FixtureChunk, ...]

    def retrieval_case(self) -> RetrievalServiceCase:
        required_chunks = [chunk for chunk in self.chunks if chunk.required]
        return RetrievalServiceCase(
            case_id=self.case_id,
            material_id=self.material_id,
            query=self.query,
            required_source_ids=[chunk.source_id for chunk in required_chunks],
            source_chunk_ids={
                chunk.source_id: chunk.chunk_id for chunk in required_chunks
            },
            source_content_sha256={
                chunk.source_id: hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
                for chunk in required_chunks
            },
        )


class BoundedEmbeddingProvider:
    """Enforce the campaign call/input ceiling and retain sanitized telemetry."""

    def __init__(self, delegate: EmbeddingProvider) -> None:
        self._delegate = delegate
        self.request_count = 0
        self.input_count = 0
        self.document_request_count = 0
        self.query_request_count = 0
        self._input_tokens: list[int | None] = []
        self._providers: set[str] = set()
        self._models: set[str] = set()

    @property
    def input_tokens(self) -> int | None:
        if not self._input_tokens or any(value is None for value in self._input_tokens):
            return None
        return sum(value for value in self._input_tokens if value is not None)

    @property
    def provider(self) -> str:
        return next(iter(self._providers)) if len(self._providers) == 1 else "unknown"

    @property
    def model(self) -> str:
        return next(iter(self._models)) if len(self._models) == 1 else "unknown"

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        next_request_count = self.request_count + 1
        next_input_count = self.input_count + len(request.inputs)
        if (
            next_request_count > MAX_EMBEDDING_REQUESTS
            or next_input_count > MAX_EMBEDDING_INPUTS
        ):
            raise RetrievalEvaluationError("embedding campaign budget exceeded")

        result = self._delegate.embed(request)
        self.request_count = next_request_count
        self.input_count = next_input_count
        if request.input_type == "search_document":
            self.document_request_count += 1
        else:
            self.query_request_count += 1
        self._input_tokens.append(result.input_tokens)
        self._providers.add(result.provider)
        self._models.add(result.model)
        if len(self._providers) != 1 or len(self._models) != 1:
            raise RetrievalEvaluationError("embedding provider binding changed during campaign")
        return result


def build_evaluation_embedding_provider() -> OpenRouterAdapter:
    """Create the exact zero-retry, no-fallback campaign provider."""
    adapter = OpenRouterAdapter(
        max_retries=0,
        routing_policy=EVALUATION_ROUTING_POLICY,
    )
    expected_routing_sha256 = hashlib.sha256(
        json.dumps(
            EVALUATION_ROUTING_POLICY.request_body(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    binding = adapter.execution_binding
    if (
        binding.max_retries != 0
        or binding.routing_policy_sha256 != expected_routing_sha256
    ):
        raise RetrievalEvaluationError("embedding execution binding mismatch")
    return adapter


def build_fixture_plan(dataset: GoldenDataset) -> list[FixtureCase]:
    """Create deterministic one-source-plus-three-distractor material fixtures."""
    rag_cases = sorted(
        (case for case in dataset.cases if case.use_case == "rag_chat"),
        key=lambda case: case.case_id,
    )
    if (
        dataset.fingerprint_sha256 != APPROVED_RETRIEVAL_POLICY_FINGERPRINT
        or not dataset.approval_verified
        or len(rag_cases) != RAG_CASE_COUNT
    ):
        raise RetrievalEvaluationError("retrieval fixture requires the approved dataset")
    if any(
        len(case.reference_context) != 1
        or case.required_source_ids != [case.reference_context[0].source_id]
        for case in rag_cases
    ):
        raise RetrievalEvaluationError("approved RAG source shape changed")
    source_ids = [case.reference_context[0].source_id for case in rag_cases]
    if len(source_ids) != len(set(source_ids)):
        raise RetrievalEvaluationError("approved RAG source IDs must be globally unique")

    fixtures: list[FixtureCase] = []
    for index, case in enumerate(rag_cases):
        selected_cases = [case] + [
            rag_cases[(index + offset) % len(rag_cases)]
            for offset in range(1, DISTRACTOR_COUNT + 1)
        ]
        chunks = tuple(
            _fixture_chunk(case, source_case, required=offset == 0)
            for offset, source_case in enumerate(selected_cases)
        )
        fixtures.append(
            FixtureCase(
                case_id=case.case_id,
                material_id=uuid5(FIXTURE_NAMESPACE, f"material:{case.case_id}"),
                query=case.input,
                chunks=chunks,
            )
        )
    return fixtures


def _fixture_chunk(
    material_case: GoldenDatasetCase,
    source_case: GoldenDatasetCase,
    *,
    required: bool,
) -> FixtureChunk:
    source = source_case.reference_context[0]
    return FixtureChunk(
        chunk_id=uuid5(
            FIXTURE_NAMESPACE,
            f"chunk:{material_case.case_id}:{source_case.case_id}:{source.source_id}",
        ),
        source_id=source.source_id,
        content=source.content,
        required=required,
    )


def sanitized_manifest(fixtures: list[FixtureCase]) -> list[dict[str, Any]]:
    """Return the content-free service manifest bound to canonical source hashes."""
    return [fixture.retrieval_case().model_dump(mode="json") for fixture in fixtures]


def persist_fixture(
    db: Session,
    fixtures: list[FixtureCase],
    provider: BoundedEmbeddingProvider,
) -> None:
    """Persist all fixture embeddings from one bounded document batch."""
    documents = [
        (fixture, chunk) for fixture in fixtures for chunk in fixture.chunks
    ]
    embedding_result = provider.embed(
        EmbeddingRequest(
            inputs=tuple(chunk.content for _, chunk in documents),
            model=settings.AI_EMBEDDING_MODEL,
            dimensions=settings.AI_EMBEDDING_DIMENSIONS,
            input_type="search_document",
        )
    )
    if len(embedding_result.embeddings) != len(documents):
        raise RetrievalEvaluationError("embedding fixture cardinality mismatch")

    owner_id = uuid5(FIXTURE_NAMESPACE, "owner")
    db.add(
        User(
            id=owner_id,
            email="rag-evaluation@example.invalid",
            password_hash="evaluation-only-not-a-password",
            full_name="RAG Evaluation",
            role="teacher",
            is_active=True,
        )
    )
    db.add_all(
        [
            StudyMaterial(
                id=fixture.material_id,
                uploader_id=owner_id,
                title=f"Retrieval fixture {fixture.case_id}",
                file_type="txt",
                file_path=f"evaluation/{fixture.case_id}.txt",
                ai_status="completed",
            )
            for fixture in fixtures
        ]
    )
    db.flush()
    db.add_all(
        [
            DocumentChunk(
                id=chunk.chunk_id,
                material_id=fixture.material_id,
                content=chunk.content,
                embedding=embedding,
            )
            for (fixture, chunk), embedding in zip(
                documents,
                embedding_result.embeddings,
                strict=True,
            )
        ]
    )
    db.commit()


def run_campaign(run_id: str, *, report_root: Path = REPORT_ROOT) -> Path:
    if settings.ENV.casefold() != "test":
        raise RetrievalEvaluationError("retrieval campaign requires test environment")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise RetrievalEvaluationError("invalid retrieval run ID")
    if not settings.OPENROUTER_API_KEY:
        raise RetrievalEvaluationError("retrieval evaluation requires provider credentials")

    output_directory = report_root / run_id
    try:
        output_directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise RetrievalEvaluationError("retrieval run output already exists") from None

    dataset = load_golden_dataset(
        DATASET_PATH,
        approval_manifest=load_approval_manifest(APPROVAL_PATH),
    )
    fixtures = build_fixture_plan(dataset)
    manifest_payload = sanitized_manifest(fixtures)
    _write_json_create_only(output_directory / "case-manifest.json", manifest_payload)

    manager = build_manager()
    evaluation_adapter = build_evaluation_embedding_provider()
    execution_binding = evaluation_adapter.execution_binding
    provider = BoundedEmbeddingProvider(evaluation_adapter)
    manager.create()
    try:
        command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
        with SessionLocal() as db:
            try:
                persist_fixture(db, fixtures, provider)
            except Exception:
                db.rollback()
                raise

            retrieval_cases = [fixture.retrieval_case() for fixture in fixtures]
            lexical_gate = _evaluate_mode(
                db,
                retrieval_cases,
                mode="lexical",
                provider=provider,
                output_path=output_directory / "lexical.report.json",
                dataset_fingerprint=dataset.fingerprint_sha256,
            )
            if not lexical_gate.evaluation_gate_passed:
                raise RetrievalEvaluationError("lexical query budget gate failed")
            hybrid_gate = _evaluate_mode(
                db,
                retrieval_cases,
                mode="hybrid",
                provider=provider,
                output_path=output_directory / "hybrid.report.json",
                dataset_fingerprint=dataset.fingerprint_sha256,
            )
            if not hybrid_gate.evaluation_gate_passed:
                raise RetrievalEvaluationError("hybrid retrieval gate failed")

        expected_requests = 1 + len(fixtures)
        expected_inputs = sum(len(item.chunks) for item in fixtures) + len(fixtures)
        if (
            provider.request_count != expected_requests
            or provider.document_request_count != 1
            or provider.query_request_count != len(fixtures)
            or provider.input_count != expected_inputs
        ):
            raise RetrievalEvaluationError("embedding campaign attestation mismatch")

        summary = {
            "schema_version": "1.0",
            "run_id": run_id,
            "dataset_fingerprint": dataset.fingerprint_sha256,
            "case_count": len(fixtures),
            "material_count": len(fixtures),
            "chunk_count": sum(len(item.chunks) for item in fixtures),
            "embedding": {
                "provider": provider.provider,
                "model": provider.model,
                "dimensions": settings.AI_EMBEDDING_DIMENSIONS,
                "request_count": provider.request_count,
                "document_request_count": provider.document_request_count,
                "query_request_count": provider.query_request_count,
                "input_count": provider.input_count,
                "input_tokens": provider.input_tokens,
                "max_request_count": MAX_EMBEDDING_REQUESTS,
                "max_retries": execution_binding.max_retries,
                "routing_policy_sha256": execution_binding.routing_policy_sha256,
                "provider_only": list(EVALUATION_ROUTING_POLICY.only),
                "allow_fallbacks": EVALUATION_ROUTING_POLICY.allow_fallbacks,
                "require_parameters": EVALUATION_ROUTING_POLICY.require_parameters,
                "data_collection": EVALUATION_ROUTING_POLICY.data_collection,
                "cost_usd": None,
            },
            "artifacts": {
                name: {
                    "file": name,
                    "sha256": _file_sha256(output_directory / name),
                }
                for name in (
                    "case-manifest.json",
                    "lexical.report.json",
                    "hybrid.report.json",
                )
            },
            "gates": {
                "lexical": lexical_gate.model_dump(mode="json"),
                "hybrid": hybrid_gate.model_dump(mode="json"),
            },
        }
        _write_json_create_only(output_directory / "summary.json", summary)
        return output_directory
    finally:
        engine.dispose()
        manager.drop_created()


def _evaluate_mode(
    db: Session,
    cases: list[RetrievalServiceCase],
    *,
    mode: Literal["lexical", "hybrid"],
    provider: BoundedEmbeddingProvider,
    output_path: Path,
    dataset_fingerprint: str,
) -> RetrievalGateAssessment:
    metrics, observations = evaluate_retrieval_service(
        db,
        cases,
        mode=mode,
        embedding_provider=provider if mode == "hybrid" else None,
    )
    gate = assess_retrieval_gate(metrics, observations)
    write_retrieval_report(
        output_path,
        metrics,
        observations,
        dataset_fingerprint=dataset_fingerprint,
        thresholds={
            "min_hit_rate": APPROVED_MIN_HIT_RATE,
            "min_source_coverage": APPROVED_MIN_SOURCE_COVERAGE,
            "max_query_count": APPROVED_MAX_QUERY_COUNT,
        },
        gate=gate,
    )
    return gate


def _write_json_create_only(path: Path, payload: object) -> None:
    if contains_secret_like_content(payload):
        raise RetrievalEvaluationError("retrieval artifact contains secret-like content")
    serialized = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RetrievalEvaluationError("retrieval artifact already exists") from None
    try:
        with os.fdopen(descriptor, "wb") as artifact:
            artifact.write(serialized)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    arguments = parser.parse_args()
    try:
        output_directory = run_campaign(arguments.run_id)
    except AIProviderError as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_code": exc.error_code,
                },
                sort_keys=True,
            )
        )
        return 1
    except RetrievalEvaluationError:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_code": "RAG_RETRIEVAL_EVALUATION_FAILED",
                },
                sort_keys=True,
            )
        )
        return 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_code": "RAG_RETRIEVAL_EVALUATION_INTERNAL_ERROR",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "run_id": arguments.run_id,
                "report_directory": str(output_directory),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
