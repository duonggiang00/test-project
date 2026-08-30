"""Evaluate an allowlisted ten-case AI-008 canary without raw stdout."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ai.evaluation.baseline_canary import (
    BaselineCanaryError,
    CanaryReport,
    FailureReplayReport,
    evaluate_canary,
    evaluate_failure_replay,
    load_canary_review_scores,
    write_canary_report,
    write_failure_replay_report,
)
from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.live_baseline import (
    V2_APPROVED_CAMPAIGN_ID,
    V3_APPROVED_CAMPAIGN_ID,
    V4_APPROVED_CAMPAIGN_ID,
    V5_APPROVED_CAMPAIGN_ID,
    V6_APPROVED_CAMPAIGN_ID,
    V7_APPROVED_CAMPAIGN_ID,
    BaselineValidationError,
    approved_campaign_root,
    load_baseline_run,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate an approved AI-008 canary without raw output."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument(
        "--campaign",
        choices=(
            V2_APPROVED_CAMPAIGN_ID,
            V3_APPROVED_CAMPAIGN_ID,
            V4_APPROVED_CAMPAIGN_ID,
            V5_APPROVED_CAMPAIGN_ID,
            V6_APPROVED_CAMPAIGN_ID,
            V7_APPROVED_CAMPAIGN_ID,
        ),
        default=V2_APPROVED_CAMPAIGN_ID,
    )
    parser.add_argument(
        "--checkpoint",
        choices=("failure-replay", "canary"),
        default="canary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=load_approval_manifest(arguments.approval_manifest),
        )
        campaign_root = approved_campaign_root(arguments.campaign)
        baseline = load_baseline_run(campaign_root / "baseline-001.candidates.json")
        report: FailureReplayReport | CanaryReport
        if arguments.checkpoint == "failure-replay":
            if arguments.campaign not in {
                V5_APPROVED_CAMPAIGN_ID,
                V6_APPROVED_CAMPAIGN_ID,
                V7_APPROVED_CAMPAIGN_ID,
            }:
                raise BaselineCanaryError(
                    "failure replay is allowlisted only for governed v5/v6 campaigns"
                )
            reviews = load_canary_review_scores(
                campaign_root / "baseline-001.failure-replay.review.jsonl"
            )
            report = evaluate_failure_replay(dataset, baseline, reviews)
            write_failure_replay_report(
                campaign_root / "baseline-001.failure-replay.report.json",
                report,
            )
        else:
            reviews = load_canary_review_scores(
                campaign_root / "baseline-001.canary.review.jsonl"
            )
            report = evaluate_canary(dataset, baseline, reviews)
            write_canary_report(
                campaign_root / "baseline-001.canary.report.json",
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
        "AI_BASELINE_CHECKPOINT_RESULT "
        f"checkpoint={arguments.checkpoint} "
        f"cases={report.case_count} "
        f"format={report.format_valid}/{report.case_count} "
        f"citations={report.citation_valid}/{report.case_count} "
        f"injection={report.injection_resistant}/{report.injection_cases} "
        f"refusals={report.explicit_refusals}/{report.explicit_refusal_cases} "
        f"continuations={report.safe_continuations}/{report.injection_cases} "
        f"passed={str(report.passed).lower()}"
    )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
