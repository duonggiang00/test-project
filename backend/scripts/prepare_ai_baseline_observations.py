"""Bind declared reviewer scores to one AI-008 candidate baseline."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from app.ai.evaluation.baseline_review import (
    BaselineReviewError,
    load_baseline_review_scores,
    prepare_reviewed_observations,
    write_reviewed_observations,
)
from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.live_baseline import (
    APPROVED_CAMPAIGN_ID,
    APPROVED_RUN_IDS,
    V2_APPROVED_CAMPAIGN_ID,
    V3_APPROVED_CAMPAIGN_ID,
    V4_APPROVED_CAMPAIGN_ID,
    V5_APPROVED_CAMPAIGN_ID,
    V6_APPROVED_CAMPAIGN_ID,
    V7_APPROVED_CAMPAIGN_ID,
    V8_APPROVED_CAMPAIGN_ID,
    BaselineValidationError,
    approved_campaign_root,
    load_baseline_run,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create AI-007 observations from a live baseline and reviewer scores."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--run-id", choices=APPROVED_RUN_IDS, required=True)
    parser.add_argument(
        "--campaign",
        choices=(
            APPROVED_CAMPAIGN_ID,
            V2_APPROVED_CAMPAIGN_ID,
            V3_APPROVED_CAMPAIGN_ID,
            V4_APPROVED_CAMPAIGN_ID,
            V5_APPROVED_CAMPAIGN_ID,
            V6_APPROVED_CAMPAIGN_ID,
            V7_APPROVED_CAMPAIGN_ID,
            V8_APPROVED_CAMPAIGN_ID,
        ),
        default=APPROVED_CAMPAIGN_ID,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    campaign_root = approved_campaign_root(arguments.campaign)
    baseline_path = campaign_root / f"{arguments.run_id}.candidates.json"
    review_scores_path = campaign_root / f"{arguments.run_id}.review.jsonl"
    output_path = campaign_root / f"{arguments.run_id}.observations.jsonl"
    try:
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=load_approval_manifest(arguments.approval_manifest),
        )
        baseline = load_baseline_run(baseline_path)
        reviews = load_baseline_review_scores(review_scores_path)
        observations = prepare_reviewed_observations(dataset, baseline, reviews)
        write_reviewed_observations(output_path, observations)
    except (
        GoldenDatasetValidationError,
        BaselineValidationError,
        BaselineReviewError,
    ) as exc:
        print(f"AI_BASELINE_REVIEW_INVALID error={exc}")
        return 1

    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    print(
        f"AI_BASELINE_REVIEW_OK cases={len(observations)} "
        f"observations_sha256={digest}"
    )
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
