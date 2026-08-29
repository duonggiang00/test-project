"""Evaluate the fixed ten-case AI-008 v2 canary without raw stdout."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ai.evaluation.baseline_canary import (
    BaselineCanaryError,
    evaluate_canary,
    load_canary_review_scores,
    write_canary_report,
)
from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.live_baseline import (
    V2_APPROVED_CAMPAIGN_ROOT,
    BaselineValidationError,
    load_baseline_run,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate the fixed AI-008 v2 canary without raw output."
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
        baseline = load_baseline_run(
            V2_APPROVED_CAMPAIGN_ROOT / "baseline-001.candidates.json"
        )
        reviews = load_canary_review_scores(
            V2_APPROVED_CAMPAIGN_ROOT / "baseline-001.canary.review.jsonl"
        )
        report = evaluate_canary(dataset, baseline, reviews)
        write_canary_report(
            V2_APPROVED_CAMPAIGN_ROOT / "baseline-001.canary.report.json",
            report,
        )
    except (
        GoldenDatasetValidationError,
        BaselineValidationError,
        BaselineCanaryError,
    ) as exc:
        print(f"AI_BASELINE_CANARY_INVALID error={exc}")
        return 1

    print(
        "AI_BASELINE_CANARY_RESULT "
        f"cases={report.case_count} "
        f"format={report.format_valid}/10 "
        f"citations={report.citation_valid}/10 "
        f"injection={report.injection_resistant}/8 "
        f"refusals={report.explicit_refusals}/{report.explicit_refusal_cases} "
        f"continuations={report.safe_continuations}/8 "
        f"passed={str(report.passed).lower()}"
    )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
