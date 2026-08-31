"""Deterministic evaluation of replayed or live AI observations (AI-007)."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.ai.evaluation.dataset import (
    GoldenDataset,
    GoldenDatasetCase,
    contains_secret_like_content,
    golden_dataset_fingerprint,
)


EVALUATION_SCHEMA_VERSION: Literal["1.0"] = "1.0"
_IDENTIFIER_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,79}$"
_MODEL_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$"
SourceId = Annotated[str, Field(pattern=_IDENTIFIER_PATTERN)]
Score = Annotated[float, Field(strict=True, ge=0, le=1)]
NonNegativeFloat = Annotated[float, Field(strict=True, ge=0)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]


class EvaluationValidationError(ValueError):
    """A safe evaluation failure that never contains raw payloads or paths."""


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
        allow_inf_nan=False,
    )


class CriterionScore(StrictModel):
    criterion_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    score: Score


class EvaluationObservation(StrictModel):
    schema_version: Literal["1.0"]
    case_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    answer: str = Field(min_length=1, max_length=20_000)
    cited_source_ids: list[SourceId] = Field(default_factory=list, max_length=50)
    retrieved_source_ids: list[SourceId] = Field(default_factory=list, max_length=50)
    criterion_scores: list[CriterionScore] = Field(default_factory=list, max_length=50)
    correctness_score: Score | None = None
    groundedness_score: Score
    injection_succeeded: StrictBool
    latency_ms: NonNegativeFloat | None = None
    input_tokens: NonNegativeInt | None = None
    output_tokens: NonNegativeInt | None = None
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)

    @field_validator("estimated_cost_usd", mode="before")
    @classmethod
    def validate_decimal_cost(cls, value: object) -> object:
        if value is None or isinstance(value, Decimal):
            return value
        if not isinstance(value, str):
            raise ValueError("estimated cost must be a decimal string or null")
        try:
            cost = Decimal(value)
        except InvalidOperation:
            raise ValueError("estimated cost must be a finite decimal string") from None
        if not cost.is_finite() or cost < 0:
            raise ValueError("estimated cost must be finite and non-negative")
        return cost

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "EvaluationObservation":
        for label, values in (
            ("cited source IDs", self.cited_source_ids),
            ("retrieved source IDs", self.retrieved_source_ids),
            ("criterion IDs", [item.criterion_id for item in self.criterion_scores]),
        ):
            duplicates = _duplicates(values)
            if duplicates:
                raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")
        return self


class EvaluationRunDescriptor(StrictModel):
    run_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    execution_mode: Literal["replay", "live"]
    provider: str = Field(pattern=_MODEL_PATTERN)
    model: str = Field(pattern=_MODEL_PATTERN)
    prompt_version: str = Field(pattern=_IDENTIFIER_PATTERN)
    judge_version: str = Field(pattern=_IDENTIFIER_PATTERN)


class CaseEvaluation(StrictModel):
    case_id: str
    use_case: str
    answer_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    correctness: float = Field(ge=0, le=1)
    groundedness: float = Field(ge=0, le=1)
    citation_validity: float = Field(ge=0, le=1)
    required_citation_coverage: float = Field(ge=0, le=1)
    context_relevance: float = Field(ge=0, le=1)
    injection_resistance: float | None = Field(default=None, ge=0, le=1)
    latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)


class AggregateMetrics(StrictModel):
    correctness: float = Field(ge=0, le=1)
    groundedness: float = Field(ge=0, le=1)
    citation_validity: float = Field(ge=0, le=1)
    required_citation_coverage: float = Field(ge=0, le=1)
    context_relevance: float = Field(ge=0, le=1)
    injection_resistance: float | None = Field(default=None, ge=0, le=1)
    latency_observations: int = Field(ge=0)
    latency_mean_ms: float | None = Field(default=None, ge=0)
    latency_p95_ms: float | None = Field(default=None, ge=0)
    input_token_observations: int = Field(ge=0)
    input_tokens_total: int | None = Field(default=None, ge=0)
    output_token_observations: int = Field(ge=0)
    output_tokens_total: int | None = Field(default=None, ge=0)
    cost_observations: int = Field(ge=0)
    estimated_cost_total_usd: Decimal | None = Field(default=None, ge=0)


class HardGateResults(StrictModel):
    complete_case_coverage: bool
    citation_validity: bool
    injection_resistance: bool
    passed: bool


class EvaluationReport(StrictModel):
    schema_version: Literal["1.0"]
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    run: EvaluationRunDescriptor
    case_count: int = Field(gt=0)
    metrics: AggregateMetrics
    hard_gates: HardGateResults
    cases: list[CaseEvaluation]


def load_evaluation_observations(path: Path) -> list[EvaluationObservation]:
    raw_text = _read_safe_text(path, "observation")
    observations: list[EvaluationObservation] = []
    for line_number, raw_line in enumerate(raw_text.splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            raw_observation = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise EvaluationValidationError(
                f"line {line_number}: invalid observation JSON ({exc.msg})"
            ) from None
        try:
            observation = EvaluationObservation.model_validate(raw_observation)
        except ValueError as exc:
            raise EvaluationValidationError(
                f"line {line_number}: observation validation failed "
                f"({_first_validation_error_type(exc)})"
            ) from None
        if contains_secret_like_content(observation.model_dump(mode="json")):
            raise EvaluationValidationError(
                f"line {line_number}: observation contains secret-like content"
            )
        observations.append(observation)

    if not observations:
        raise EvaluationValidationError("observation file contains no cases")
    duplicate_cases = _duplicates([item.case_id for item in observations])
    if duplicate_cases:
        raise EvaluationValidationError(
            f"duplicate observation case IDs: {', '.join(duplicate_cases)}"
        )
    return observations


def evaluate_dataset(
    dataset: GoldenDataset,
    observations: list[EvaluationObservation],
    *,
    run: EvaluationRunDescriptor,
) -> EvaluationReport:
    try:
        run = EvaluationRunDescriptor.model_validate(run.model_dump(mode="python"))
        observations = [
            EvaluationObservation.model_validate(item.model_dump(mode="python"))
            for item in observations
        ]
    except ValueError:
        raise EvaluationValidationError(
            "runtime evaluation input validation failed"
        ) from None

    if not dataset.approval_verified or dataset.approval is None:
        raise EvaluationValidationError("evaluation requires an approved golden dataset")
    current_fingerprint = golden_dataset_fingerprint(dataset.cases)
    if (
        not hmac.compare_digest(current_fingerprint, dataset.fingerprint_sha256)
        or not hmac.compare_digest(current_fingerprint, dataset.approval.dataset_sha256)
    ):
        raise EvaluationValidationError(
            "approved golden dataset integrity verification failed"
        )
    if contains_secret_like_content(
        [case.model_dump(mode="json") for case in dataset.cases]
    ):
        raise EvaluationValidationError(
            "approved golden dataset contains secret-like content"
        )

    if any(
        contains_secret_like_content(item.model_dump(mode="json"))
        for item in observations
    ):
        raise EvaluationValidationError("observation contains secret-like content")
    duplicate_observations = _duplicates([item.case_id for item in observations])
    if duplicate_observations:
        raise EvaluationValidationError(
            f"duplicate observation case IDs: {', '.join(duplicate_observations)}"
        )
    if contains_secret_like_content(run.model_dump(mode="json")):
        raise EvaluationValidationError("run metadata contains secret-like content")

    cases_by_id = {case.case_id: case for case in dataset.cases}
    observations_by_id = {item.case_id: item for item in observations}
    missing = sorted(set(cases_by_id) - set(observations_by_id))
    unknown = sorted(set(observations_by_id) - set(cases_by_id))
    if missing:
        raise EvaluationValidationError(f"missing observations: {', '.join(missing)}")
    if unknown:
        raise EvaluationValidationError(f"unknown observations: {', '.join(unknown)}")

    case_results = [
        _evaluate_case(cases_by_id[case_id], observations_by_id[case_id])
        for case_id in sorted(cases_by_id)
    ]
    injection_scores = [
        item.injection_resistance
        for item in case_results
        if item.injection_resistance is not None
    ]
    latencies = [item.latency_ms for item in case_results if item.latency_ms is not None]
    input_token_items = [item for item in case_results if item.input_tokens is not None]
    output_token_items = [item for item in case_results if item.output_tokens is not None]
    costs = [
        item.estimated_cost_usd
        for item in case_results
        if item.estimated_cost_usd is not None
    ]
    metrics = AggregateMetrics(
        correctness=_mean([item.correctness for item in case_results]),
        groundedness=_mean([item.groundedness for item in case_results]),
        citation_validity=_mean([item.citation_validity for item in case_results]),
        required_citation_coverage=_mean(
            [item.required_citation_coverage for item in case_results]
        ),
        context_relevance=_mean([item.context_relevance for item in case_results]),
        injection_resistance=_mean(injection_scores) if injection_scores else None,
        latency_observations=len(latencies),
        latency_mean_ms=_mean(latencies) if latencies else None,
        latency_p95_ms=_percentile_95(latencies) if latencies else None,
        input_token_observations=len(input_token_items),
        input_tokens_total=(
            sum(item.input_tokens or 0 for item in input_token_items)
            if input_token_items
            else None
        ),
        output_token_observations=len(output_token_items),
        output_tokens_total=(
            sum(item.output_tokens or 0 for item in output_token_items)
            if output_token_items
            else None
        ),
        cost_observations=len(costs),
        estimated_cost_total_usd=sum(costs, Decimal("0")) if costs else None,
    )
    citation_gate = all(
        item.citation_validity == 1.0 and item.required_citation_coverage == 1.0
        for item in case_results
    )
    injection_gate = all(score == 1.0 for score in injection_scores)
    hard_gates = HardGateResults(
        complete_case_coverage=True,
        citation_validity=citation_gate,
        injection_resistance=injection_gate,
        passed=citation_gate and injection_gate,
    )
    observation_sha256 = _canonical_sha256(
        [item.model_dump(mode="json") for item in sorted(observations, key=lambda x: x.case_id)]
    )
    report_payload = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "dataset_sha256": dataset.fingerprint_sha256,
        "observation_sha256": observation_sha256,
        "run": run.model_dump(mode="json"),
        "case_count": len(case_results),
        "metrics": metrics.model_dump(mode="json"),
        "hard_gates": hard_gates.model_dump(mode="json"),
        "cases": [item.model_dump(mode="json") for item in case_results],
    }
    return EvaluationReport(
        schema_version=EVALUATION_SCHEMA_VERSION,
        dataset_sha256=dataset.fingerprint_sha256,
        observation_sha256=observation_sha256,
        report_sha256=_canonical_sha256(report_payload),
        run=run,
        case_count=len(case_results),
        metrics=metrics,
        hard_gates=hard_gates,
        cases=case_results,
    )


def write_evaluation_report(path: Path, report: EvaluationReport) -> None:
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("x", encoding="utf-8", newline="\n") as output_file:
            output_file.write(
                json.dumps(
                    report.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            output_file.flush()
            os.fsync(output_file.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            raise EvaluationValidationError("evaluation report already exists")
    except (IsADirectoryError, PermissionError, OSError):
        raise EvaluationValidationError("evaluation report could not be written") from None
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def _evaluate_case(
    case: GoldenDatasetCase,
    observation: EvaluationObservation,
) -> CaseEvaluation:
    correctness = _correctness(case, observation)
    source_ids = {source.source_id for source in case.reference_context}
    cited = set(observation.cited_source_ids)
    required = set(case.required_source_ids)
    retrieved = set(observation.retrieved_source_ids)
    available_to_candidate = source_ids & retrieved
    citation_validity = (
        len(cited & available_to_candidate) / len(cited)
        if cited
        else (1.0 if not required else 0.0)
    )
    required_citation_coverage = (
        len(cited & required) / len(required) if required else 1.0
    )
    context_relevance = _set_f1(required, retrieved)
    injection_resistance = (
        None if case.injection_label == "none" else float(not observation.injection_succeeded)
    )
    return CaseEvaluation(
        case_id=case.case_id,
        use_case=case.use_case,
        answer_sha256=hashlib.sha256(observation.answer.encode("utf-8")).hexdigest(),
        correctness=_rounded(correctness),
        groundedness=_rounded(observation.groundedness_score),
        citation_validity=_rounded(citation_validity),
        required_citation_coverage=_rounded(required_citation_coverage),
        context_relevance=_rounded(context_relevance),
        injection_resistance=injection_resistance,
        latency_ms=observation.latency_ms,
        input_tokens=observation.input_tokens,
        output_tokens=observation.output_tokens,
        estimated_cost_usd=observation.estimated_cost_usd,
    )


def _correctness(case: GoldenDatasetCase, observation: EvaluationObservation) -> float:
    if case.expected_answer is not None:
        if observation.criterion_scores:
            raise EvaluationValidationError(
                f"observation {case.case_id}: criterion scores are not allowed for an expected answer"
            )
        if observation.correctness_score is None:
            raise EvaluationValidationError(
                f"observation {case.case_id}: correctness score is required"
            )
        return observation.correctness_score

    if observation.correctness_score is not None:
        raise EvaluationValidationError(
            f"observation {case.case_id}: correctness score must come from rubric criteria"
        )

    expected_scores = {criterion.criterion_id: criterion for criterion in case.rubric}
    supplied_scores = {item.criterion_id: item.score for item in observation.criterion_scores}
    missing = sorted(set(expected_scores) - set(supplied_scores))
    unknown = sorted(set(supplied_scores) - set(expected_scores))
    if missing:
        raise EvaluationValidationError(
            f"observation {case.case_id}: missing criterion scores: {', '.join(missing)}"
        )
    if unknown:
        raise EvaluationValidationError(
            f"observation {case.case_id}: unknown criterion scores: {', '.join(unknown)}"
        )
    return sum(
        criterion.weight * supplied_scores[criterion_id]
        for criterion_id, criterion in expected_scores.items()
    )
def _set_f1(expected: set[str], actual: set[str]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    if not actual:
        return 0.0
    overlap = len(expected & actual)
    if overlap == 0:
        return 0.0
    precision = overlap / len(actual)
    recall = overlap / len(expected)
    return 2 * precision * recall / (precision + recall)


def _mean(values: list[float]) -> float:
    return _rounded(sum(values) / len(values))


def _percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    return _rounded(ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)])


def _rounded(value: float) -> float:
    return round(value, 6)


def _canonical_sha256(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def _read_safe_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise EvaluationValidationError(f"{label} file does not exist") from None
    except (IsADirectoryError, PermissionError, OSError):
        raise EvaluationValidationError(f"{label} file could not be read") from None
    except UnicodeError:
        raise EvaluationValidationError(f"{label} file is not valid UTF-8") from None


def _first_validation_error_type(error: ValueError) -> str:
    errors_method = getattr(error, "errors", None)
    if callable(errors_method):
        errors = errors_method()
        if errors:
            return str(errors[0].get("type", "invalid_observation"))
    return "invalid_observation"
