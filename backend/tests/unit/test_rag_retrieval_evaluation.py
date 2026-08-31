from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import hashlib
import json

import pytest

from app.ai.evaluation.rag_retrieval import (
    RetrievalEvaluationError,
    RetrievalMetrics,
    RetrievalObservation,
    RetrievalResult,
    RetrievalServiceCase,
    assess_retrieval_gate,
    evaluate_retrieval,
    evaluate_retrieval_service,
    write_retrieval_report,
)
from app.ai.provider import EmbeddingRequest, EmbeddingResult
from app.models.document_chunk import DocumentChunk
import scripts.evaluate_rag_retrieval as retrieval_cli
import scripts.run_rag_retrieval_evaluation as retrieval_runner


def _case(case_id, required):
    return SimpleNamespace(case_id=case_id, use_case="rag_chat", required_source_ids=required)


@pytest.mark.unit
def test_retrieval_evaluation_is_deterministic_and_content_free(tmp_path: Path):
    cases = [_case("rag-002", ["source-b"]), _case("rag-001", ["source-a"])]

    def retrieve(case, mode):
        return RetrievalResult(
            source_ids=[case.required_source_ids[0]],
            query_count=1 if mode == "lexical" else 2,
        )

    metrics, observations = evaluate_retrieval(cases, mode="hybrid", retrieve=retrieve)
    assert metrics.case_count == 2
    assert metrics.hit_rate_at_k == 1
    assert metrics.source_coverage == 1
    assert [item.case_id for item in observations] == ["rag-001", "rag-002"]

    report = tmp_path / "retrieval.json"
    write_retrieval_report(report, metrics, observations)
    text = report.read_text(encoding="utf-8")
    assert "source-a" in text
    assert "content" not in text
    with pytest.raises(RetrievalEvaluationError, match="already exists"):
        write_retrieval_report(report, metrics, observations)


@pytest.mark.unit
def test_retrieval_evaluation_rejects_duplicate_sources():
    with pytest.raises(RetrievalEvaluationError, match="duplicate"):
        evaluate_retrieval(
            [_case("rag-001", ["source-a"])],
            mode="lexical",
            retrieve=lambda case, mode: RetrievalResult(["source-a", "source-a"], 1),
        )


@pytest.mark.unit
def test_retrieval_service_evaluation_uses_production_service_and_counts_queries():
    material_id = uuid4()
    source_id = uuid4()
    chunk = DocumentChunk(
        id=source_id,
        material_id=material_id,
        content="vector retrieval",
        embedding=[0.0] * 1536,
    )

    class FakeScalars:
        def all(self):
            return [chunk]

    class FakeSession:
        def scalars(self, statement):
            assert "document_chunks.material_id" in str(statement)
            return FakeScalars()

    metrics, observations = evaluate_retrieval_service(
        FakeSession(),
        [
            RetrievalServiceCase(
                case_id="rag-service-001",
                material_id=material_id,
                query="vector",
                required_source_ids=[str(source_id)],
                source_chunk_ids={str(source_id): source_id},
                source_content_sha256={
                    str(source_id): hashlib.sha256(b"vector retrieval").hexdigest()
                },
            )
        ],
        mode="lexical",
    )

    assert metrics.case_count == 1
    assert metrics.hit_rate_at_k == 1
    assert observations[0].query_count == 1


@pytest.mark.unit
def test_retrieval_service_evaluation_rejects_tampered_chunk_mapping():
    material_id = uuid4()
    source_id = uuid4()
    chunk = DocumentChunk(
        id=source_id,
        material_id=material_id,
        content="distractor",
        embedding=[0.0] * 1536,
    )

    class FakeScalars:
        def all(self):
            return [chunk]

    class FakeSession:
        def scalars(self, statement):
            return FakeScalars()

    case = RetrievalServiceCase(
        case_id="rag-service-tampered",
        material_id=material_id,
        query="vector",
        required_source_ids=["canonical-source"],
        source_chunk_ids={"canonical-source": source_id},
        source_content_sha256={
            "canonical-source": hashlib.sha256(b"approved content").hexdigest()
        },
    )
    with pytest.raises(RetrievalEvaluationError, match="content binding"):
        evaluate_retrieval_service(FakeSession(), [case], mode="lexical")


@pytest.mark.unit
def test_cli_requires_exact_approved_rag_case_set_and_fingerprint(tmp_path, monkeypatch):
    approved_content = "approved content"
    golden_cases = [
        SimpleNamespace(
            case_id=f"rag-{index:03d}",
            input=f"query-{index}",
            required_source_ids=[f"source-{index}"],
            reference_context=[
                SimpleNamespace(source_id=f"source-{index}", content=approved_content)
            ],
            use_case="rag_chat",
        )
        for index in range(1, 17)
    ]
    fingerprint = "4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51"
    monkeypatch.setattr(
        retrieval_cli,
        "load_golden_dataset",
        lambda *args, **kwargs: SimpleNamespace(
            cases=golden_cases, fingerprint_sha256=fingerprint
        ),
    )
    monkeypatch.setattr(retrieval_cli, "load_approval_manifest", lambda path: object())
    manifest = tmp_path / "cases.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "case_id": case.case_id,
                    "material_id": str(uuid4()),
                    "query": case.input,
                    "required_source_ids": case.required_source_ids,
                    "source_chunk_ids": {
                        case.required_source_ids[0]: str(uuid4())
                    },
                    "source_content_sha256": {
                        case.required_source_ids[0]: hashlib.sha256(
                            approved_content.encode()
                        ).hexdigest()
                    },
                }
                for case in golden_cases
            ]
        ),
        encoding="utf-8",
    )

    cases, loaded_fingerprint = retrieval_cli._load_approved_cases(
        manifest, tmp_path / "dataset.jsonl", tmp_path / "approval.json"
    )
    assert len(cases) == 16
    assert loaded_fingerprint == fingerprint

    records = json.loads(manifest.read_text(encoding="utf-8"))
    records.append(records[0])
    manifest.write_text(json.dumps(records), encoding="utf-8")
    with pytest.raises(RetrievalEvaluationError, match="does not match"):
        retrieval_cli._load_approved_cases(
            manifest, tmp_path / "dataset.jsonl", tmp_path / "approval.json"
        )


@pytest.mark.unit
def test_lexical_baseline_does_not_claim_activation_when_quality_is_below_floor():
    metrics = RetrievalMetrics(
        mode="lexical",
        case_count=1,
        hit_rate_at_k=0,
        mean_reciprocal_rank=0,
        source_coverage=0,
        mean_query_count=2,
    )
    observations = [
        RetrievalObservation(
            case_id="rag-001",
            mode="lexical",
            retrieved_source_ids=[],
            query_count=2,
            latency_ms=1,
        )
    ]

    gate = assess_retrieval_gate(metrics, observations)

    assert gate.activation_eligible is False
    assert gate.quality_gate_enforced is False
    assert gate.quality_thresholds_met is False
    assert gate.query_budget_met is True
    assert gate.evaluation_gate_passed is True


@pytest.mark.unit
def test_hybrid_candidate_requires_quality_and_query_budget():
    metrics = RetrievalMetrics(
        mode="hybrid",
        case_count=1,
        hit_rate_at_k=0,
        mean_reciprocal_rank=0,
        source_coverage=0,
        mean_query_count=3,
    )
    observations = [
        RetrievalObservation(
            case_id="rag-001",
            mode="hybrid",
            retrieved_source_ids=[],
            query_count=3,
            latency_ms=1,
        )
    ]

    gate = assess_retrieval_gate(metrics, observations)

    assert gate.activation_eligible is False
    assert gate.quality_gate_enforced is True
    assert gate.quality_thresholds_met is False
    assert gate.query_budget_met is False
    assert gate.evaluation_gate_passed is False


@pytest.mark.unit
def test_passing_hybrid_candidate_is_activation_eligible():
    metrics = RetrievalMetrics(
        mode="hybrid",
        case_count=1,
        hit_rate_at_k=1,
        mean_reciprocal_rank=1,
        source_coverage=1,
        mean_query_count=2,
    )
    observations = [
        RetrievalObservation(
            case_id="rag-001",
            mode="hybrid",
            retrieved_source_ids=["source-1"],
            query_count=2,
            latency_ms=1,
        )
    ]

    gate = assess_retrieval_gate(metrics, observations)

    assert gate.activation_eligible is True
    assert gate.evaluation_gate_passed is True


@pytest.mark.unit
def test_fixture_plan_is_deterministic_bounded_and_content_free():
    dataset = retrieval_runner.load_golden_dataset(
        retrieval_runner.DATASET_PATH,
        approval_manifest=retrieval_runner.load_approval_manifest(
            retrieval_runner.APPROVAL_PATH
        ),
    )

    first = retrieval_runner.build_fixture_plan(dataset)
    second = retrieval_runner.build_fixture_plan(dataset)
    manifest = retrieval_runner.sanitized_manifest(first)
    serialized_manifest = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    assert first == second
    assert len(first) == 16
    assert all(len(item.chunks) == 4 for item in first)
    assert all(sum(chunk.required for chunk in item.chunks) == 1 for item in first)
    assert len({item.material_id for item in first}) == 16
    assert len({chunk.chunk_id for item in first for chunk in item.chunks}) == 64
    assert len(manifest) == 16
    assert all("content" not in item for item in manifest)
    assert all(
        source.content not in serialized_manifest
        for case in dataset.cases
        if case.use_case == "rag_chat"
        for source in case.reference_context
    )


@pytest.mark.unit
def test_embedding_campaign_budget_stops_before_an_extra_provider_call():
    class FakeEmbeddingProvider:
        def __init__(self):
            self.calls = 0

        def embed(self, request):
            self.calls += 1
            return EmbeddingResult(
                embeddings=[[0.0] for _ in request.inputs],
                provider="fake",
                model=request.model,
                input_tokens=len(request.inputs),
                latency_ms=1,
            )

    delegate = FakeEmbeddingProvider()
    provider = retrieval_runner.BoundedEmbeddingProvider(delegate)
    request = EmbeddingRequest(
        inputs=("bounded",),
        model="embedding-test",
        dimensions=1,
        input_type="search_query",
    )

    for _ in range(retrieval_runner.MAX_EMBEDDING_REQUESTS):
        provider.embed(request)

    with pytest.raises(RetrievalEvaluationError, match="budget exceeded"):
        provider.embed(request)
    assert delegate.calls == retrieval_runner.MAX_EMBEDDING_REQUESTS


@pytest.mark.unit
def test_campaign_provider_is_zero_retry_and_no_fallback():
    adapter = retrieval_runner.build_evaluation_embedding_provider()
    binding = adapter.execution_binding

    assert binding.max_retries == 0
    assert binding.routing_policy_sha256 is not None
    assert retrieval_runner.EVALUATION_ROUTING_POLICY.request_body() == {
        "only": ["openai"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
    }


@pytest.mark.unit
def test_fixture_persistence_uses_one_document_batch():
    dataset = retrieval_runner.load_golden_dataset(
        retrieval_runner.DATASET_PATH,
        approval_manifest=retrieval_runner.load_approval_manifest(
            retrieval_runner.APPROVAL_PATH
        ),
    )
    fixtures = retrieval_runner.build_fixture_plan(dataset)

    class FakeEmbeddingProvider:
        def embed(self, request):
            return EmbeddingResult(
                embeddings=[[0.0] * request.dimensions for _ in request.inputs],
                provider="fake",
                model=request.model,
                input_tokens=len(request.inputs),
                latency_ms=1,
            )

    class FakeSession:
        def __init__(self):
            self.added = []
            self.flushes = 0
            self.commits = 0

        def add(self, value):
            self.added.append(value)

        def add_all(self, values):
            self.added.extend(values)

        def flush(self):
            self.flushes += 1

        def commit(self):
            self.commits += 1

    provider = retrieval_runner.BoundedEmbeddingProvider(FakeEmbeddingProvider())
    db = FakeSession()

    retrieval_runner.persist_fixture(db, fixtures, provider)

    assert provider.request_count == 1
    assert provider.document_request_count == 1
    assert provider.query_request_count == 0
    assert provider.input_count == 64
    assert sum(isinstance(item, DocumentChunk) for item in db.added) == 64
    assert db.flushes == 1
    assert db.commits == 1


@pytest.mark.unit
def test_campaign_cli_sanitizes_evaluation_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        retrieval_runner,
        "run_campaign",
        lambda run_id: (_ for _ in ()).throw(
            RetrievalEvaluationError("raw source must remain hidden")
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["run_rag_retrieval_evaluation", "--run-id", "safe-run-001"],
    )

    assert retrieval_runner.main() == 1
    output = capsys.readouterr().out
    assert "RAG_RETRIEVAL_EVALUATION_FAILED" in output
    assert "raw source" not in output


@pytest.mark.unit
def test_campaign_refuses_non_test_runtime_before_creating_output(tmp_path):
    if retrieval_runner.settings.ENV.casefold() == "test":
        pytest.skip("the process is already explicitly isolated for integration")

    with pytest.raises(RetrievalEvaluationError, match="requires test environment"):
        retrieval_runner.run_campaign("safe-run-001", report_root=tmp_path)
    assert list(tmp_path.iterdir()) == []
