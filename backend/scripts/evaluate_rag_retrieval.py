"""Run the sanitized RAG retrieval evaluation against PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Literal

from app.ai import default_embedding_provider
from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.rag_retrieval import (
    APPROVED_MIN_HIT_RATE,
    APPROVED_MAX_QUERY_COUNT,
    APPROVED_MIN_SOURCE_COVERAGE,
    APPROVED_RETRIEVAL_POLICY_FINGERPRINT,
    RetrievalEvaluationError,
    RetrievalServiceCase,
    assess_retrieval_gate,
    evaluate_retrieval_service,
    write_retrieval_report,
)
from app.db.session import SessionLocal


def _load_cases(path: Path) -> list[RetrievalServiceCase]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("case manifest must be a JSON array")
        return [
            RetrievalServiceCase.model_validate_json(json.dumps(item))
            for item in payload
        ]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RetrievalEvaluationError("invalid retrieval case manifest") from exc


def _load_approved_cases(
    manifest_path: Path,
    dataset_path: Path,
    approval_path: Path,
) -> tuple[list[RetrievalServiceCase], str]:
    try:
        dataset = load_golden_dataset(
            dataset_path,
            approval_manifest=load_approval_manifest(approval_path),
        )
        cases = _load_cases(manifest_path)
    except (GoldenDatasetValidationError, RetrievalEvaluationError) as exc:
        raise RetrievalEvaluationError("approved retrieval inputs are invalid") from exc
    expected = {
        case.case_id: (
            case.input,
            tuple(case.required_source_ids),
            tuple(sorted(source.source_id for source in case.reference_context)),
            tuple(
                sorted(
                    (
                        source.source_id,
                        hashlib.sha256(source.content.encode("utf-8")).hexdigest(),
                    )
                    for source in case.reference_context
                )
            ),
        )
        for case in dataset.cases
        if case.use_case == "rag_chat"
    }
    actual = {
        case.case_id: (
            case.query,
            tuple(case.required_source_ids),
            tuple(sorted(case.source_chunk_ids)),
            tuple(sorted(case.source_content_sha256.items())),
        )
        for case in cases
    }
    if (
        dataset.fingerprint_sha256 != APPROVED_RETRIEVAL_POLICY_FINGERPRINT
        or len(expected) != 16
        or len(cases) != 16
        or len(actual) != len(cases)
        or actual != expected
    ):
        raise RetrievalEvaluationError("retrieval manifest does not match approved RAG cases")
    return cases, dataset.fingerprint_sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("lexical", "hybrid"), required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    mode: Literal["lexical", "hybrid"] = args.mode
    cases, dataset_fingerprint = _load_approved_cases(
        args.manifest, args.dataset, args.approval_manifest
    )
    with SessionLocal() as db:
        metrics, observations = evaluate_retrieval_service(
            db,
            cases,
            mode=mode,
            embedding_provider=default_embedding_provider if mode == "hybrid" else None,
        )
    gate = assess_retrieval_gate(metrics, observations)
    write_retrieval_report(
        args.report,
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
    if not gate.evaluation_gate_passed:
        raise RetrievalEvaluationError("retrieval quality or query budget gate failed")
    print(
        json.dumps(
            {
                "case_count": metrics.case_count,
                "mode": metrics.mode,
                "report": str(args.report),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
