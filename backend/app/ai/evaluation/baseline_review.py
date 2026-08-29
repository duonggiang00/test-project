"""Reviewer-score binding for AI-008 live baseline candidates."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.evaluation.dataset import GoldenDataset
from app.ai.evaluation.live_baseline import (
    BaselineRunFile,
    BaselineValidationError,
    validate_approved_campaign_binding,
)
from app.ai.evaluation.runner import (
    CriterionScore,
    EvaluationObservation,
    EvaluationValidationError,
)


_IDENTIFIER_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,79}$"
Score = Annotated[float, Field(strict=True, ge=0, le=1)]


class BaselineReviewError(ValueError):
    """A safe review-binding failure without raw candidate output or paths."""


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
        allow_inf_nan=False,
        frozen=True,
    )


class BaselineReviewScore(StrictModel):
    case_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    criterion_scores: list[CriterionScore] = Field(default_factory=list, max_length=50)
    correctness_score: Score | None = None
    groundedness_score: Score
    injection_succeeded: bool = Field(strict=True)


def load_baseline_review_scores(path: Path) -> list[BaselineReviewScore]:
    """Load strict JSONL scores while keeping validation messages value-free."""
    try:
        raw_text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise BaselineReviewError("review score file does not exist") from None
    except (IsADirectoryError, PermissionError, OSError, UnicodeError):
        raise BaselineReviewError("review score file could not be read") from None

    scores: list[BaselineReviewScore] = []
    for line_number, raw_line in enumerate(raw_text.splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            raw_score = json.loads(raw_line)
            score = BaselineReviewScore.model_validate(raw_score)
        except json.JSONDecodeError:
            raise BaselineReviewError(
                f"line {line_number}: invalid review score JSON"
            ) from None
        except ValueError:
            raise BaselineReviewError(
                f"line {line_number}: review score validation failed"
            ) from None
        scores.append(score)

    if not scores:
        raise BaselineReviewError("review score file contains no cases")
    duplicate_ids = _duplicates([score.case_id for score in scores])
    if duplicate_ids:
        raise BaselineReviewError("review score file contains duplicate case IDs")
    return scores


def prepare_reviewed_observations(
    dataset: GoldenDataset,
    baseline: BaselineRunFile,
    reviews: list[BaselineReviewScore],
) -> list[EvaluationObservation]:
    """Bind reviewer judgments to candidates without deriving semantic scores."""
    try:
        baseline = BaselineRunFile.model_validate(
            baseline.model_dump(mode="python")
        )
        reviews = [
            BaselineReviewScore.model_validate(review.model_dump(mode="python"))
            for review in reviews
        ]
    except ValueError:
        raise BaselineReviewError("review binding input validation failed") from None
    if not dataset.approval_verified or dataset.approval is None:
        raise BaselineReviewError("review requires an approved golden dataset")
    try:
        validate_approved_campaign_binding(dataset, baseline.run)
    except BaselineValidationError:
        raise BaselineReviewError(
            "baseline does not match the approved campaign"
        ) from None

    cases_by_id = {case.case_id: case for case in dataset.cases}
    attempts_by_id = {attempt.case_id: attempt for attempt in baseline.attempts}
    reviews_by_id = {review.case_id: review for review in reviews}
    expected_ids = set(cases_by_id)
    if set(attempts_by_id) != expected_ids:
        raise BaselineReviewError("baseline candidate coverage is incomplete")
    if set(reviews_by_id) != expected_ids:
        raise BaselineReviewError("review score coverage is incomplete")
    reviewable_statuses = {"succeeded", "invalid_response"}
    if any(attempt.status not in reviewable_statuses for attempt in baseline.attempts):
        raise BaselineReviewError("baseline contains an unsuccessful provider attempt")

    observations: list[EvaluationObservation] = []
    for case_id in sorted(expected_ids):
        attempt = attempts_by_id[case_id]
        review = reviews_by_id[case_id]
        if not attempt.answer:
            raise BaselineReviewError("baseline contains an empty candidate answer")
        try:
            observation = EvaluationObservation.model_validate(
                {
                    "schema_version": "1.0",
                    "case_id": case_id,
                    "answer": attempt.answer,
                    "cited_source_ids": attempt.cited_source_ids or [],
                    "retrieved_source_ids": attempt.retrieved_source_ids or [],
                    "criterion_scores": review.criterion_scores,
                    "correctness_score": review.correctness_score,
                    "groundedness_score": review.groundedness_score,
                    "injection_succeeded": review.injection_succeeded,
                    "latency_ms": attempt.latency_ms,
                    "input_tokens": attempt.input_tokens,
                    "output_tokens": attempt.output_tokens,
                    "estimated_cost_usd": None,
                }
            )
        except ValueError:
            raise BaselineReviewError(
                "reviewed observation validation failed"
            ) from None
        observations.append(observation)
    return observations


def write_reviewed_observations(
    path: Path, observations: list[EvaluationObservation]
) -> None:
    """Publish reviewer-bound JSONL once without overwriting another result."""
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("x", encoding="utf-8", newline="\n") as output_file:
            for observation in sorted(observations, key=lambda item: item.case_id):
                output_file.write(
                    json.dumps(
                        observation.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
            output_file.flush()
            os.fsync(output_file.fileno())
        os.link(temporary_path, path)
    except FileExistsError:
        raise BaselineReviewError("reviewed observation file already exists") from None
    except (IsADirectoryError, PermissionError, OSError):
        raise BaselineReviewError(
            "reviewed observation file could not be written"
        ) from None
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)
