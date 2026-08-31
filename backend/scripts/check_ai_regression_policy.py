"""Check sanitized AI-008 V8 evidence against the owner-approved policy."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.regression_policy import (
    AIRegressionPolicyError,
    evaluate_ai008_v8_comparison,
    load_approved_baseline_comparison,
    validate_ai008_pr_subset_baseline,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check reviewer-bound AI-008 evidence without raw output."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("comparison", type=Path)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument(
        "--pr-subset-baseline",
        type=Path,
        default=Path("evals/baselines/ai-008-v8.pr-subset-baseline.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=load_approval_manifest(arguments.approval_manifest),
        )
        comparison = load_approved_baseline_comparison(arguments.comparison)
        validate_ai008_pr_subset_baseline(dataset, arguments.pr_subset_baseline)
        result = evaluate_ai008_v8_comparison(dataset, comparison)
    except (GoldenDatasetValidationError, AIRegressionPolicyError) as exc:
        print(f"AI_REGRESSION_POLICY_INVALID error={exc}")
        return 1

    if not result.passed:
        print(
            "AI_REGRESSION_POLICY_FAILED "
            f"runs={result.checked_runs} "
            f"failures={','.join(result.failure_codes)} "
            "cost_gate=inactive"
        )
        return 1
    print(
        f"AI_REGRESSION_POLICY_OK runs={result.checked_runs} "
        "subset_cases=20 failures=0 cost_gate=inactive"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
