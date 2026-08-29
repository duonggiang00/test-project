"""Create the sanitized AI-008 three-run comparison artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ai.evaluation.baseline_comparison import (
    BaselineComparisonError,
    compare_baselines,
    load_evaluation_report,
    write_baseline_comparison,
)
from app.ai.evaluation.baseline_review import (
    BaselineReviewError,
    load_baseline_review_scores,
)
from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.live_baseline import (
    APPROVED_CAMPAIGN_ROOT,
    APPROVED_RUN_IDS,
    BaselineValidationError,
    load_baseline_run,
)
from app.ai.evaluation.runner import (
    EvaluationValidationError,
    load_evaluation_observations,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare the three approved AI-008 baselines without raw output."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=load_approval_manifest(arguments.approval_manifest),
        )
        candidates = [
            load_baseline_run(
                APPROVED_CAMPAIGN_ROOT / f"{run_id}.candidates.json"
            )
            for run_id in APPROVED_RUN_IDS
        ]
        reports = [
            load_evaluation_report(APPROVED_CAMPAIGN_ROOT / f"{run_id}.report.json")
            for run_id in APPROVED_RUN_IDS
        ]
        observations_by_run = {
            run_id: load_evaluation_observations(
                APPROVED_CAMPAIGN_ROOT / f"{run_id}.observations.jsonl"
            )
            for run_id in APPROVED_RUN_IDS
        }
        reviews_by_run = {
            run_id: load_baseline_review_scores(
                APPROVED_CAMPAIGN_ROOT / f"{run_id}.review.jsonl"
            )
            for run_id in APPROVED_RUN_IDS
        }
        comparison = compare_baselines(
            dataset,
            candidates,
            reports,
            observations_by_run,
            reviews_by_run,
        )
        write_baseline_comparison(
            APPROVED_CAMPAIGN_ROOT / "comparison.json", comparison
        )
    except (
        GoldenDatasetValidationError,
        BaselineValidationError,
        BaselineComparisonError,
        BaselineReviewError,
        EvaluationValidationError,
    ) as exc:
        print(f"AI_BASELINE_COMPARISON_INVALID error={exc}")
        return 1

    print(
        "AI_BASELINE_COMPARISON_OK "
        f"calls={comparison.total_calls} "
        f"format_valid={comparison.format_valid_total}/{comparison.total_calls} "
        f"hard_gate_runs={comparison.hard_gate_passed_runs}/3 "
        f"acceptance_ready={str(comparison.baseline_acceptance_ready).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
