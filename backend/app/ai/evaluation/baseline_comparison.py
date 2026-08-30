"""Sanitized comparison of three governed AI-008 baseline reports."""

from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.evaluation.baseline_review import (
    BaselineReviewError,
    BaselineReviewScore,
    prepare_reviewed_observations,
)
from app.ai.evaluation.dataset import GoldenDataset
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
    BaselineRunFile,
    validate_approved_campaign_binding,
)
from app.ai.evaluation.runner import (
    EvaluationObservation,
    EvaluationReport,
    EvaluationValidationError,
    HardGateResults,
    evaluate_dataset,
)


COMPARISON_SCHEMA_VERSION: Literal["1.0"] = "1.0"
APPROVED_JUDGE_VERSION = "codex-independent-review-v1"


class BaselineComparisonError(ValueError):
    """A safe comparison failure without raw evaluation content or paths."""


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
        allow_inf_nan=False,
        frozen=True,
    )


class MetricRange(StrictModel):
    minimum: float
    median: float
    maximum: float


class BaselineRunSummary(StrictModel):
    run_id: str
    attempts: int = Field(ge=0)
    format_valid: int = Field(ge=0)
    format_invalid_case_ids: list[str]
    hard_gates: HardGateResults
    correctness: float = Field(ge=0, le=1)
    groundedness: float = Field(ge=0, le=1)
    citation_validity: float = Field(ge=0, le=1)
    required_citation_coverage: float = Field(ge=0, le=1)
    context_relevance: float = Field(ge=0, le=1)
    injection_resistance: float | None = Field(default=None, ge=0, le=1)
    latency_observations: int = Field(ge=0)
    latency_p95_ms: float | None = Field(default=None, ge=0)
    input_token_observations: int = Field(ge=0)
    input_tokens_total: int | None = Field(default=None, ge=0)
    output_token_observations: int = Field(ge=0)
    output_tokens_total: int | None = Field(default=None, ge=0)
    cost_observations: int = Field(ge=0)
    estimated_cost_total_usd: Decimal | None = Field(default=None, ge=0)
    observation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BaselineComparison(StrictModel):
    schema_version: Literal["1.0"]
    campaign_id: str = APPROVED_CAMPAIGN_ID
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider: str
    model: str
    prompt_version: str
    response_format: Literal["json_object"] | None = None
    response_parse_mode: Literal["extract_json_payload"] | None = None
    routing_policy_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    case_order_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    judge_version: str
    total_calls: Literal[120]
    format_valid_total: int = Field(ge=0, le=120)
    hard_gate_passed_runs: int = Field(ge=0, le=3)
    baseline_acceptance_ready: bool
    metrics: dict[str, MetricRange]
    runs: list[BaselineRunSummary] = Field(min_length=3, max_length=3)


def compare_baselines(
    dataset: GoldenDataset,
    candidates: list[BaselineRunFile],
    reports: list[EvaluationReport],
    observations_by_run: dict[str, list[EvaluationObservation]],
    reviews_by_run: dict[str, list[BaselineReviewScore]],
    *,
    expected_campaign_id: str = APPROVED_CAMPAIGN_ID,
) -> BaselineComparison:
    """Validate comparability and return a raw-output-free three-run summary."""
    try:
        candidates = [
            BaselineRunFile.model_validate(item.model_dump(mode="python"))
            for item in candidates
        ]
        reports = [
            EvaluationReport.model_validate(item.model_dump(mode="python"))
            for item in reports
        ]
    except ValueError:
        raise BaselineComparisonError("baseline comparison input validation failed") from None

    candidates_by_id = {item.run.run_id: item for item in candidates}
    reports_by_id = {item.run.run_id: item for item in reports}
    if len(candidates) != 3 or len(reports) != 3:
        raise BaselineComparisonError("comparison requires the three approved runs")
    if set(candidates_by_id) != set(APPROVED_RUN_IDS) or set(reports_by_id) != set(
        APPROVED_RUN_IDS
    ):
        raise BaselineComparisonError("comparison requires the three approved runs")
    if set(observations_by_run) != set(APPROVED_RUN_IDS):
        raise BaselineComparisonError("comparison requires observations for every run")
    if set(reviews_by_run) != set(APPROVED_RUN_IDS):
        raise BaselineComparisonError("comparison requires reviews for every run")
    if expected_campaign_id not in {
        APPROVED_CAMPAIGN_ID,
        V2_APPROVED_CAMPAIGN_ID,
        V3_APPROVED_CAMPAIGN_ID,
        V4_APPROVED_CAMPAIGN_ID,
        V5_APPROVED_CAMPAIGN_ID,
        V6_APPROVED_CAMPAIGN_ID,
        V7_APPROVED_CAMPAIGN_ID,
        V8_APPROVED_CAMPAIGN_ID,
    } or any(
        candidate.run.campaign_id != expected_campaign_id
        for candidate in candidates
    ):
        raise BaselineComparisonError(
            "comparison candidates do not match the requested campaign"
        )

    summaries: list[BaselineRunSummary] = []
    for run_id in APPROVED_RUN_IDS:
        candidate = candidates_by_id[run_id]
        report = reports_by_id[run_id]
        try:
            validate_approved_campaign_binding(dataset, candidate.run)
        except ValueError:
            raise BaselineComparisonError(
                "candidate does not match the approved campaign"
            ) from None
        if len(candidate.attempts) != 40 or any(
            attempt.status not in {"succeeded", "invalid_response"}
            or (attempt.status == "succeeded")
            != (attempt.response_format_valid is True)
            for attempt in candidate.attempts
        ):
            raise BaselineComparisonError("candidate run is not fully attempted")
        if (
            report.dataset_sha256 != dataset.fingerprint_sha256
            or report.case_count != 40
            or report.run.run_id != run_id
            or report.run.execution_mode != "live"
            or report.run.provider != candidate.run.provider
            or report.run.model != candidate.run.model
            or report.run.prompt_version != candidate.run.prompt_version
            or report.run.judge_version != APPROVED_JUDGE_VERSION
        ):
            raise BaselineComparisonError(
                "evaluation report does not match the approved candidate run"
            )
        if not _report_integrity_valid(report):
            raise BaselineComparisonError("evaluation report integrity check failed")
        try:
            expected_observations = prepare_reviewed_observations(
                dataset,
                candidate,
                reviews_by_run[run_id],
            )
            actual_observations = sorted(
                observations_by_run[run_id], key=lambda item: item.case_id
            )
            if expected_observations != actual_observations:
                raise BaselineComparisonError(
                    "evaluation observations do not match candidates and reviews"
                )
            expected_report = evaluate_dataset(
                dataset,
                actual_observations,
                run=report.run,
            )
        except (BaselineReviewError, EvaluationValidationError):
            raise BaselineComparisonError(
                "evaluation observations failed deterministic validation"
            ) from None
        if expected_report != report:
            raise BaselineComparisonError(
                "evaluation report does not match deterministic observations"
            )
        attempts_by_id = {attempt.case_id: attempt for attempt in candidate.attempts}
        cases_by_id = {case.case_id: case for case in report.cases}
        expected_case_ids = {case.case_id for case in dataset.cases}
        if (
            len(cases_by_id) != 40
            or set(cases_by_id) != expected_case_ids
            or set(attempts_by_id) != expected_case_ids
            or any(
                cases_by_id[case_id].answer_sha256
                != hashlib.sha256(
                    (attempts_by_id[case_id].answer or "").encode("utf-8")
                ).hexdigest()
                for case_id in expected_case_ids
            )
        ):
            raise BaselineComparisonError(
                "evaluation report is not bound to the candidate answers"
            )
        if report.hard_gates.passed != (
            report.hard_gates.complete_case_coverage
            and report.hard_gates.citation_validity
            and report.hard_gates.injection_resistance
        ):
            raise BaselineComparisonError("evaluation report hard gates are inconsistent")
        invalid_ids = sorted(
            attempt.case_id
            for attempt in candidate.attempts
            if attempt.status == "invalid_response"
        )
        metrics = report.metrics
        summaries.append(
            BaselineRunSummary(
                run_id=run_id,
                attempts=len(candidate.attempts),
                format_valid=sum(
                    attempt.response_format_valid is True
                    for attempt in candidate.attempts
                ),
                format_invalid_case_ids=invalid_ids,
                hard_gates=report.hard_gates,
                correctness=metrics.correctness,
                groundedness=metrics.groundedness,
                citation_validity=metrics.citation_validity,
                required_citation_coverage=metrics.required_citation_coverage,
                context_relevance=metrics.context_relevance,
                injection_resistance=metrics.injection_resistance,
                latency_observations=metrics.latency_observations,
                latency_p95_ms=metrics.latency_p95_ms,
                input_token_observations=metrics.input_token_observations,
                input_tokens_total=metrics.input_tokens_total,
                output_token_observations=metrics.output_token_observations,
                output_tokens_total=metrics.output_tokens_total,
                cost_observations=metrics.cost_observations,
                estimated_cost_total_usd=metrics.estimated_cost_total_usd,
                observation_sha256=report.observation_sha256,
                report_sha256=report.report_sha256,
            )
        )

    ranges = {
        name: _metric_range([float(getattr(run, name)) for run in summaries])
        for name in (
            "correctness",
            "groundedness",
            "citation_validity",
            "required_citation_coverage",
            "context_relevance",
        )
    }
    injection_values = [
        run.injection_resistance
        for run in summaries
        if run.injection_resistance is not None
    ]
    if len(injection_values) == 3:
        ranges["injection_resistance"] = _metric_range(injection_values)
    latency_values = [
        run.latency_p95_ms for run in summaries if run.latency_p95_ms is not None
    ]
    if len(latency_values) == 3:
        ranges["latency_p95_ms"] = _metric_range(latency_values)

    format_valid_total = sum(run.format_valid for run in summaries)
    passed_runs = sum(run.hard_gates.passed for run in summaries)
    return BaselineComparison(
        schema_version=COMPARISON_SCHEMA_VERSION,
        campaign_id=expected_campaign_id,
        dataset_sha256=dataset.fingerprint_sha256,
        provider=candidates_by_id[APPROVED_RUN_IDS[0]].run.provider,
        model=candidates_by_id[APPROVED_RUN_IDS[0]].run.model,
        prompt_version=candidates_by_id[APPROVED_RUN_IDS[0]].run.prompt_version,
        response_format=candidates_by_id[APPROVED_RUN_IDS[0]].run.response_format,
        response_parse_mode=candidates_by_id[APPROVED_RUN_IDS[0]].run.response_parse_mode,
        routing_policy_sha256=candidates_by_id[
            APPROVED_RUN_IDS[0]
        ].run.routing_policy_sha256,
        case_order_sha256=candidates_by_id[
            APPROVED_RUN_IDS[0]
        ].run.case_order_sha256,
        judge_version=APPROVED_JUDGE_VERSION,
        total_calls=120,
        format_valid_total=format_valid_total,
        hard_gate_passed_runs=passed_runs,
        baseline_acceptance_ready=(format_valid_total == 120 and passed_runs == 3),
        metrics=ranges,
        runs=summaries,
    )


def load_evaluation_report(path: Path) -> EvaluationReport:
    """Load one sanitized report without exposing local paths or values in errors."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return EvaluationReport.model_validate(raw)
    except FileNotFoundError:
        raise BaselineComparisonError("evaluation report does not exist") from None
    except json.JSONDecodeError:
        raise BaselineComparisonError("evaluation report contains invalid JSON") from None
    except ValueError:
        raise BaselineComparisonError("evaluation report validation failed") from None
    except (IsADirectoryError, PermissionError, OSError, UnicodeError):
        raise BaselineComparisonError("evaluation report could not be read") from None


def write_baseline_comparison(path: Path, comparison: BaselineComparison) -> None:
    """Publish one sanitized comparison without overwriting prior evidence."""
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = comparison.model_dump(mode="json")
        if comparison.campaign_id not in {
            V4_APPROVED_CAMPAIGN_ID,
            V5_APPROVED_CAMPAIGN_ID,
            V6_APPROVED_CAMPAIGN_ID,
            V7_APPROVED_CAMPAIGN_ID,
            V8_APPROVED_CAMPAIGN_ID,
        }:
            payload.pop("response_parse_mode", None)
        with temporary_path.open("x", encoding="utf-8", newline="\n") as output_file:
            output_file.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            output_file.flush()
            os.fsync(output_file.fileno())
        os.link(temporary_path, path)
    except FileExistsError:
        raise BaselineComparisonError("baseline comparison already exists") from None
    except (IsADirectoryError, PermissionError, OSError):
        raise BaselineComparisonError("baseline comparison could not be written") from None
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def _metric_range(values: list[float]) -> MetricRange:
    return MetricRange(
        minimum=round(min(values), 6),
        median=round(float(median(values)), 6),
        maximum=round(max(values), 6),
    )


def _report_integrity_valid(report: EvaluationReport) -> bool:
    payload = report.model_dump(mode="json")
    expected_sha256 = payload.pop("report_sha256")
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest() == expected_sha256
