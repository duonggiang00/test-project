from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai.evaluation.baseline_review import (
    BaselineReviewError,
    BaselineReviewScore,
    load_baseline_review_scores,
    prepare_reviewed_observations,
    write_reviewed_observations,
)
from app.ai.evaluation.dataset import load_approval_manifest, load_golden_dataset
from app.ai.evaluation.live_baseline import (
    BASELINE_PROMPT_VERSION,
    BASELINE_SCHEMA_VERSION,
    APPROVED_MODEL,
    PROMPT_TEMPLATE_SHA256,
    BaselineRunDescriptor,
    _collect_live_baseline,
)
from app.ai.evaluation.runner import EvaluationRunDescriptor, evaluate_dataset
from tests.unit.test_ai_live_baseline import FakeProvider


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.jsonl"
APPROVAL_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.approval.json"


def _dataset():
    return load_golden_dataset(
        DATASET_PATH,
        approval_manifest=load_approval_manifest(APPROVAL_PATH),
    )


def _baseline(tmp_path: Path):
    dataset = _dataset()
    run = BaselineRunDescriptor.model_validate(
        {
            "schema_version": BASELINE_SCHEMA_VERSION,
            "campaign_id": "ai-008-v1",
            "run_id": "baseline-001",
            "dataset_sha256": dataset.fingerprint_sha256,
            "provider": "openrouter",
            "model": APPROVED_MODEL,
            "prompt_version": BASELINE_PROMPT_VERSION,
            "prompt_template_sha256": PROMPT_TEMPLATE_SHA256,
            "temperature": 0.0,
            "max_output_tokens": 1000,
        }
    )
    return _collect_live_baseline(
        dataset,
        output_path=tmp_path / "baseline.json",
        budget_path=tmp_path / "campaign.json",
        run=run,
        provider=FakeProvider(),
        max_new_calls=40,
    )


def _reviews() -> list[BaselineReviewScore]:
    reviews = []
    for case in _dataset().cases:
        reviews.append(
            BaselineReviewScore.model_validate(
                {
                    "case_id": case.case_id,
                    "criterion_scores": [
                        {"criterion_id": criterion.criterion_id, "score": 1.0}
                        for criterion in case.rubric
                    ],
                    "correctness_score": (
                        1.0 if case.expected_answer is not None else None
                    ),
                    "groundedness_score": 1.0,
                    "injection_succeeded": False,
                }
            )
        )
    return reviews


def test_review_scores_bind_to_all_candidates_and_pass_into_ai007(
    tmp_path: Path,
) -> None:
    observations = prepare_reviewed_observations(
        _dataset(), _baseline(tmp_path), _reviews()
    )

    report = evaluate_dataset(
        _dataset(),
        observations,
        run=EvaluationRunDescriptor.model_validate(
            {
                "run_id": "baseline-001",
                "execution_mode": "live",
                "provider": "openrouter",
                "model": APPROVED_MODEL,
                "prompt_version": BASELINE_PROMPT_VERSION,
                "judge_version": "manual-review-v1",
            }
        ),
    )

    assert len(observations) == 40
    assert report.case_count == 40
    assert report.hard_gates.passed is True
    assert report.metrics.cost_observations == 0
    assert report.metrics.estimated_cost_total_usd is None


def test_review_binding_rejects_incomplete_candidate_or_score_coverage(
    tmp_path: Path,
) -> None:
    baseline = _baseline(tmp_path)

    with pytest.raises(BaselineReviewError, match="score coverage is incomplete"):
        prepare_reviewed_observations(_dataset(), baseline, _reviews()[:-1])

    incomplete = baseline.model_copy(update={"attempts": baseline.attempts[:-1]})
    with pytest.raises(BaselineReviewError, match="candidate coverage is incomplete"):
        prepare_reviewed_observations(_dataset(), incomplete, _reviews())


def test_review_binding_rejects_non_campaign_provider_metadata(tmp_path: Path) -> None:
    baseline = _baseline(tmp_path)
    unapproved = baseline.model_copy(
        update={"run": baseline.run.model_copy(update={"model": "other/model"})}
    )

    with pytest.raises(BaselineReviewError, match="approved campaign"):
        prepare_reviewed_observations(_dataset(), unapproved, _reviews())


def test_review_score_loader_is_strict_and_value_safe(tmp_path: Path) -> None:
    path = tmp_path / "scores.jsonl"
    raw = _reviews()[0].model_dump(mode="json")
    raw["groundedness_score"] = "1.0"
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    with pytest.raises(BaselineReviewError, match="validation failed") as error:
        load_baseline_review_scores(path)

    assert "1.0" not in str(error.value)
    assert str(path) not in str(error.value)


def test_reviewed_observation_writer_is_create_only(tmp_path: Path) -> None:
    observations = prepare_reviewed_observations(
        _dataset(), _baseline(tmp_path), _reviews()
    )
    output = tmp_path / "observations.jsonl"
    write_reviewed_observations(output, observations)
    original = output.read_bytes()

    with pytest.raises(BaselineReviewError, match="already exists"):
        write_reviewed_observations(output, observations)

    assert output.read_bytes() == original
