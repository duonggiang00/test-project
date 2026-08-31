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
    V3_APPROVED_CAMPAIGN_ID,
    V3_APPROVED_MODEL,
    V3_BASELINE_PROMPT_VERSION,
    V3_BASELINE_SCHEMA_VERSION,
    V3_PROMPT_TEMPLATE_SHA256,
    V4_APPROVED_CAMPAIGN_ID,
    V4_APPROVED_MODEL,
    V4_BASELINE_PROMPT_VERSION,
    V4_BASELINE_SCHEMA_VERSION,
    V4_PROMPT_TEMPLATE_SHA256,
    V4_RESPONSE_PARSE_MODE,
    V5_APPROVED_CAMPAIGN_ID,
    V5_APPROVED_MODEL,
    V5_BASELINE_PROMPT_VERSION,
    V5_BASELINE_SCHEMA_VERSION,
    V5_PROMPT_TEMPLATE_SHA256,
    V5_RESPONSE_PARSE_MODE,
    V6_APPROVED_CAMPAIGN_ID,
    V6_APPROVED_MODEL,
    V6_BASELINE_PROMPT_VERSION,
    V6_BASELINE_SCHEMA_VERSION,
    V6_PROMPT_TEMPLATE_SHA256,
    V6_RESPONSE_PARSE_MODE,
    V7_APPROVED_CAMPAIGN_ID,
    V7_APPROVED_MODEL,
    V7_BASELINE_PROMPT_VERSION,
    V7_BASELINE_SCHEMA_VERSION,
    V7_PROMPT_TEMPLATE_SHA256,
    V7_RESPONSE_PARSE_MODE,
    V8_APPROVED_CAMPAIGN_ID,
    V8_APPROVED_MODEL,
    V8_BASELINE_PROMPT_VERSION,
    V8_BASELINE_SCHEMA_VERSION,
    V8_PROMPT_TEMPLATE_SHA256,
    V8_RESPONSE_PARSE_MODE,
    V8_ROUTING_POLICY_SHA256,
    V8_ROUTING_PROVIDER_SLUG,
    V8_UPSTREAM_PROVIDER,
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
    try:
        if settings.AI_PROVIDER != APPROVED_PROVIDER:
            raise BaselineValidationError(
                "configured provider does not match the approved campaign"
            )
        if (
            arguments.campaign
            not in {
                V3_APPROVED_CAMPAIGN_ID,
                V4_APPROVED_CAMPAIGN_ID,
                V5_APPROVED_CAMPAIGN_ID,
                V6_APPROVED_CAMPAIGN_ID,
                V7_APPROVED_CAMPAIGN_ID,
                V8_APPROVED_CAMPAIGN_ID,
            }
            and settings.AI_DEFAULT_MODEL != APPROVED_MODEL
        ):
            raise BaselineValidationError(
                "configured model does not match the approved campaign"
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
        is_v3 = arguments.campaign == V3_APPROVED_CAMPAIGN_ID
        is_v4 = arguments.campaign == V4_APPROVED_CAMPAIGN_ID
        is_v5 = arguments.campaign == V5_APPROVED_CAMPAIGN_ID
        is_v6 = arguments.campaign == V6_APPROVED_CAMPAIGN_ID
        is_v7 = arguments.campaign == V7_APPROVED_CAMPAIGN_ID
        is_v8 = arguments.campaign == V8_APPROVED_CAMPAIGN_ID
        is_governed = (
            is_v2 or is_v3 or is_v4 or is_v5 or is_v6 or is_v7 or is_v8
        )
        run = BaselineRunDescriptor.model_validate(
            {
                "schema_version": (
                    V8_BASELINE_SCHEMA_VERSION
                    if is_v8
                    else V7_BASELINE_SCHEMA_VERSION
                    if is_v7
                    else V6_BASELINE_SCHEMA_VERSION
                    if is_v6
                    else V5_BASELINE_SCHEMA_VERSION
                    if is_v5
                    else V4_BASELINE_SCHEMA_VERSION
                    if is_v4
                    else V3_BASELINE_SCHEMA_VERSION
                    if is_v3
                    else V2_BASELINE_SCHEMA_VERSION
                    if is_v2
                    else BASELINE_SCHEMA_VERSION
                ),
                "campaign_id": arguments.campaign,
                "run_id": arguments.run_id,
                "dataset_sha256": dataset.fingerprint_sha256,
                "provider": APPROVED_PROVIDER,
                "model": (
                    V8_APPROVED_MODEL
                    if is_v8
                    else V7_APPROVED_MODEL
                    if is_v7
                    else V6_APPROVED_MODEL
                    if is_v6
                    else V5_APPROVED_MODEL
                    if is_v5
                    else V4_APPROVED_MODEL
                    if is_v4
                    else V3_APPROVED_MODEL
                    if is_v3
                    else APPROVED_MODEL
                ),
                "prompt_version": (
                    V8_BASELINE_PROMPT_VERSION
                    if is_v8
                    else V7_BASELINE_PROMPT_VERSION
                    if is_v7
                    else V6_BASELINE_PROMPT_VERSION
                    if is_v6
                    else V5_BASELINE_PROMPT_VERSION
                    if is_v5
                    else V4_BASELINE_PROMPT_VERSION
                    if is_v4
                    else V3_BASELINE_PROMPT_VERSION
                    if is_v3
                    else V2_BASELINE_PROMPT_VERSION
                    if is_v2
                    else BASELINE_PROMPT_VERSION
                ),
                "prompt_template_sha256": (
                    V8_PROMPT_TEMPLATE_SHA256
                    if is_v8
                    else V7_PROMPT_TEMPLATE_SHA256
                    if is_v7
                    else V6_PROMPT_TEMPLATE_SHA256
                    if is_v6
                    else V5_PROMPT_TEMPLATE_SHA256
                    if is_v5
                    else V4_PROMPT_TEMPLATE_SHA256
                    if is_v4
                    else V3_PROMPT_TEMPLATE_SHA256
                    if is_v3
                    else V2_PROMPT_TEMPLATE_SHA256
                    if is_v2
                    else PROMPT_TEMPLATE_SHA256
                ),
                "temperature": APPROVED_TEMPERATURE,
                "max_output_tokens": APPROVED_MAX_OUTPUT_TOKENS,
                "response_format": V2_RESPONSE_FORMAT if is_governed else None,
                "routing_policy_sha256": (
                    V8_ROUTING_POLICY_SHA256
                    if is_v8
                    else V2_ROUTING_POLICY_SHA256
                    if is_governed
                    else None
                ),
                "case_order_sha256": (
                    approved_case_order_sha256(dataset, arguments.campaign)
                    if is_governed
                    else None
                ),
                "response_parse_mode": (
                    V8_RESPONSE_PARSE_MODE
                    if is_v8
                    else V7_RESPONSE_PARSE_MODE
                    if is_v7
                    else V6_RESPONSE_PARSE_MODE
                    if is_v6
                    else V5_RESPONSE_PARSE_MODE
                    if is_v5
                    else V4_RESPONSE_PARSE_MODE
                    if is_v4
                    else None
                ),
            }
        )
        routing_policy = (
            OpenRouterRoutingPolicy(
                only=(
                    V8_ROUTING_PROVIDER_SLUG if is_v8 else V2_UPSTREAM_PROVIDER,
                ),
                allow_fallbacks=False,
                require_parameters=True,
                data_collection="deny",
            )
            if is_governed
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
