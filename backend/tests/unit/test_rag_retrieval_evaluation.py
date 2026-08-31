from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import hashlib
import json

import pytest

from app.ai.evaluation.rag_retrieval import (
    RetrievalEvaluationError,
    RetrievalResult,
    RetrievalServiceCase,
    evaluate_retrieval,
    evaluate_retrieval_service,
    write_retrieval_report,
)
from app.models.document_chunk import DocumentChunk
import scripts.evaluate_rag_retrieval as retrieval_cli


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
