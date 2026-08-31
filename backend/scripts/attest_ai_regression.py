"""Validate independent semantic review evidence for an AI regression run."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.regression_collection import (
    AIRegressionCollectionError,
    attest_ai008_regression,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bind independent review scores to one AI regression candidate file."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("collection_manifest", type=Path)
    parser.add_argument("reviews", type=Path)
    parser.add_argument("attestation", type=Path)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--reviewer-actor", required=True)
    parser.add_argument("--review-ref", required=True)
    parser.add_argument("--expected-commit-sha", required=True)
    parser.add_argument("--collection-run-id", required=True)
    parser.add_argument("--candidate-artifact-digest", required=True)
    parser.add_argument("--collection-manifest-artifact-digest", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=load_approval_manifest(arguments.approval_manifest),
        )
        attestation = attest_ai008_regression(
            dataset,
            candidate_path=arguments.candidates,
            collection_manifest_path=arguments.collection_manifest,
            review_path=arguments.reviews,
            collection_run_id=arguments.collection_run_id,
            candidate_artifact_digest=arguments.candidate_artifact_digest,
            collection_manifest_artifact_digest=(arguments.collection_manifest_artifact_digest),
            reviewer_actor=arguments.reviewer_actor,
            review_ref=arguments.review_ref,
            expected_commit_sha=arguments.expected_commit_sha,
            attestation_path=arguments.attestation,
        )
    except (GoldenDatasetValidationError, AIRegressionCollectionError) as exc:
        print(f"AI_REGRESSION_ATTESTATION_INVALID error={exc}")
        return 1
    except ValueError:
        print("AI_REGRESSION_ATTESTATION_INVALID error=attestation validation failed")
        return 1

    if not attestation.passed:
        print(
            "AI_REGRESSION_ATTESTATION_FAILED "
            f"scope={attestation.scope} failures={','.join(attestation.failure_codes)} "
            "cost_gate=inactive"
        )
        return 1
    print(
        f"AI_REGRESSION_ATTESTATION_OK scope={attestation.scope} "
        f"cases={attestation.case_count} failures=0 cost_gate=inactive"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
