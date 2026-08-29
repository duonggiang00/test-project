"""Collect a capped AI-008 live baseline through the provider abstraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.live_baseline import (
    BASELINE_PROMPT_VERSION,
    BASELINE_SCHEMA_VERSION,
    APPROVED_CAMPAIGN_ID,
    APPROVED_MAX_OUTPUT_TOKENS,
    APPROVED_MODEL,
    APPROVED_PROVIDER,
    APPROVED_RUN_IDS,
    APPROVED_TEMPERATURE,
    PROMPT_TEMPLATE_SHA256,
    V2_APPROVED_CAMPAIGN_ID,
    V2_BASELINE_PROMPT_VERSION,
    V2_BASELINE_SCHEMA_VERSION,
    V2_PROMPT_TEMPLATE_SHA256,
    V2_RESPONSE_FORMAT,
    V2_ROUTING_POLICY_SHA256,
    V2_UPSTREAM_PROVIDER,
    approved_case_order_sha256,
    BaselineProviderFailure,
    BaselineResponseFailure,
    BaselineRunDescriptor,
    BaselineValidationError,
    collect_approved_live_baseline,
)
from app.ai.openrouter_adapter import OpenRouterAdapter, OpenRouterRoutingPolicy
from app.core.config import settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect capped live AI observations without printing raw output."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--run-id", choices=APPROVED_RUN_IDS, required=True)
    parser.add_argument("--max-new-calls", type=int, required=True)
    parser.add_argument(
        "--campaign",
        choices=(APPROVED_CAMPAIGN_ID, V2_APPROVED_CAMPAIGN_ID),
        default=APPROVED_CAMPAIGN_ID,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if (
            settings.AI_PROVIDER != APPROVED_PROVIDER
            or settings.AI_DEFAULT_MODEL != APPROVED_MODEL
        ):
            raise BaselineValidationError(
                "configured provider/model does not match the approved campaign"
            )
        if not settings.OPENROUTER_API_KEY.strip():
            raise BaselineValidationError(
                "approved campaign requires a configured provider credential"
            )
        approval = load_approval_manifest(arguments.approval_manifest)
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=approval,
        )
        is_v2 = arguments.campaign == V2_APPROVED_CAMPAIGN_ID
        run = BaselineRunDescriptor.model_validate(
            {
                "schema_version": (
                    V2_BASELINE_SCHEMA_VERSION if is_v2 else BASELINE_SCHEMA_VERSION
                ),
                "campaign_id": arguments.campaign,
                "run_id": arguments.run_id,
                "dataset_sha256": dataset.fingerprint_sha256,
                "provider": APPROVED_PROVIDER,
                "model": APPROVED_MODEL,
                "prompt_version": (
                    V2_BASELINE_PROMPT_VERSION if is_v2 else BASELINE_PROMPT_VERSION
                ),
                "prompt_template_sha256": (
                    V2_PROMPT_TEMPLATE_SHA256 if is_v2 else PROMPT_TEMPLATE_SHA256
                ),
                "temperature": APPROVED_TEMPERATURE,
                "max_output_tokens": APPROVED_MAX_OUTPUT_TOKENS,
                "response_format": V2_RESPONSE_FORMAT if is_v2 else None,
                "routing_policy_sha256": (
                    V2_ROUTING_POLICY_SHA256 if is_v2 else None
                ),
                "case_order_sha256": (
                    approved_case_order_sha256(dataset, arguments.campaign)
                    if is_v2
                    else None
                ),
            }
        )
        routing_policy = (
            OpenRouterRoutingPolicy(
                only=(V2_UPSTREAM_PROVIDER,),
                allow_fallbacks=False,
                require_parameters=True,
                data_collection="deny",
            )
            if is_v2
            else None
        )
        state = collect_approved_live_baseline(
            dataset,
            run=run,
            provider=OpenRouterAdapter(
                max_retries=0,
                routing_policy=routing_policy,
            ),
            max_new_calls=arguments.max_new_calls,
        )
    except BaselineProviderFailure as exc:
        print(f"AI_BASELINE_PROVIDER_FAILED error={exc}")
        return 1
    except BaselineResponseFailure as exc:
        print(f"AI_BASELINE_RESPONSE_INVALID error={exc}")
        return 1
    except (GoldenDatasetValidationError, BaselineValidationError, ValueError) as exc:
        error = (
            str(exc)
            if isinstance(
                exc, (GoldenDatasetValidationError, BaselineValidationError)
            )
            else "baseline run validation failed"
        )
        print(f"AI_BASELINE_INVALID error={error}")
        return 1

    succeeded = sum(attempt.status == "succeeded" for attempt in state.attempts)
    invalid = sum(attempt.status == "invalid_response" for attempt in state.attempts)
    valid_envelopes = sum(
        attempt.response_format_valid is True for attempt in state.attempts
    )
    attempted = succeeded + invalid
    if attempted == len(dataset.cases) and invalid:
        status = "AI_BASELINE_COMPLETE_WITH_INVALID_RESPONSES"
    elif succeeded == len(dataset.cases):
        status = "AI_BASELINE_COMPLETE"
    else:
        status = "AI_BASELINE_PARTIAL"
    print(
        f"{status} run_id={state.run.run_id} attempts={attempted}/{len(dataset.cases)} "
        f"format_valid={valid_envelopes}/{attempted} prompt={state.run.prompt_version}"
    )
    return 1 if invalid else 0
if __name__ == "__main__":
    raise SystemExit(main())
