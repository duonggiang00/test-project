"""Run the protected 20/40-case AI-008 V8 collection schedule."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.regression_collection import (
    AIRegressionCollectionError,
    collect_ai008_regression,
)
from app.ai.evaluation.live_baseline import V8_ROUTING_PROVIDER_SLUG
from app.ai.openrouter_adapter import OpenRouterAdapter, OpenRouterRoutingPolicy
from app.core.config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Collect the approved AI-008 V8 regression scope without printing candidate content."
        )
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--scope", choices=("pr", "full"), required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-key", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if not _safe_run_key(arguments.run_key):
        print("AI_REGRESSION_COLLECTION_INVALID error=run identity is invalid")
        return 1
    if settings.AI_PROVIDER != "openrouter" or not settings.OPENROUTER_API_KEY.strip():
        print("AI_REGRESSION_COLLECTION_INVALID error=provider configuration is invalid")
        return 1

    output_root = BACKEND_ROOT / "reports" / "ai-regression" / arguments.run_key
    try:
        approval = load_approval_manifest(arguments.approval_manifest)
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=approval,
        )
        manifest = collect_ai008_regression(
            dataset,
            scope=arguments.scope,
            commit_sha=arguments.commit_sha,
            provider=OpenRouterAdapter(
                max_retries=0,
                routing_policy=OpenRouterRoutingPolicy(
                    only=(V8_ROUTING_PROVIDER_SLUG,),
                    allow_fallbacks=False,
                    require_parameters=True,
                    data_collection="deny",
                ),
            ),
            candidate_path=output_root / "candidates.json",
            manifest_path=output_root / "manifest.json",
        )
    except (GoldenDatasetValidationError, AIRegressionCollectionError) as exc:
        print(f"AI_REGRESSION_COLLECTION_FAILED error={exc}")
        return 1
    except ValueError:
        print("AI_REGRESSION_COLLECTION_INVALID error=collection validation failed")
        return 1

    status = (
        "AI_REGRESSION_COLLECTION_OK"
        if manifest.structural_gate_passed
        else "AI_REGRESSION_COLLECTION_REJECTED"
    )
    print(
        f"{status} scope={manifest.scope} cases={manifest.case_count} "
        f"semantic={manifest.semantic_status} cost_gate=inactive"
    )
    return 0 if manifest.structural_gate_passed else 1


def _safe_run_key(value: str) -> bool:
    return 1 <= len(value) <= 80 and all(
        character.isascii() and (character.isalnum() or character in "-._") for character in value
    )


if __name__ == "__main__":
    raise SystemExit(main())
