from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.ai.evaluation.baseline_comparison import (
    APPROVED_JUDGE_VERSION,
    BaselineComparisonError,
    compare_baselines,
    write_baseline_comparison,
)
from app.ai.evaluation.baseline_review import prepare_reviewed_observations
from app.ai.evaluation.live_baseline import (
    APPROVED_RUN_IDS,
    BaselineRunFile,
)
from app.ai.evaluation.runner import (
    EvaluationObservation,
    EvaluationReport,
    EvaluationRunDescriptor,
    evaluate_dataset,
)
from tests.unit.test_ai_baseline_review import _baseline, _dataset, _reviews


def _candidates(tmp_path: Path) -> list[BaselineRunFile]:
    first = _baseline(tmp_path)
    return [
        BaselineRunFile.model_validate(
            first.model_copy(
                update={"run": first.run.model_copy(update={"run_id": run_id})}
            ).model_dump(mode="python")
        )
        for run_id in APPROVED_RUN_IDS
    ]


def _report_and_observations(
    candidate: BaselineRunFile,
) -> tuple[EvaluationReport, list[EvaluationObservation]]:
    observations = prepare_reviewed_observations(
        _dataset(), candidate, _reviews()
    )
    report = evaluate_dataset(
        _dataset(),
        observations,
        run=EvaluationRunDescriptor.model_validate(
            {
                "run_id": candidate.run.run_id,
                "execution_mode": "live",
                "provider": candidate.run.provider,
                "model": candidate.run.model,
                "prompt_version": candidate.run.prompt_version,
                "judge_version": APPROVED_JUDGE_VERSION,
            }
        ),
    )
    return report, observations


def _evidence(candidate: BaselineRunFile):
    report, observations = _report_and_observations(candidate)
    return report, observations, _reviews()


def _compare(candidates: list[BaselineRunFile]):
    evidence = {
        candidate.run.run_id: _evidence(candidate) for candidate in candidates
    }
    return compare_baselines(
        _dataset(),
        candidates,
        [evidence[run_id][0] for run_id in APPROVED_RUN_IDS],
        {run_id: evidence[run_id][1] for run_id in APPROVED_RUN_IDS},
        {run_id: evidence[run_id][2] for run_id in APPROVED_RUN_IDS},
    )


def _rehash(report: EvaluationReport) -> EvaluationReport:
    payload = report.model_dump(mode="json")
    payload.pop("report_sha256")
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return report.model_copy(
        update={"report_sha256": hashlib.sha256(canonical).hexdigest()}
    )


def test_comparison_requires_exact_three_runs_and_reports(tmp_path: Path) -> None:
    candidates = _candidates(tmp_path)
    evidence = {
        candidate.run.run_id: _evidence(candidate) for candidate in candidates
    }
    reports = [evidence[run_id][0] for run_id in APPROVED_RUN_IDS]
    observations = {run_id: evidence[run_id][1] for run_id in APPROVED_RUN_IDS}
    reviews = {run_id: evidence[run_id][2] for run_id in APPROVED_RUN_IDS}

    comparison = compare_baselines(
        _dataset(), candidates, reports, observations, reviews
    )

    assert comparison.total_calls == 120
    assert comparison.format_valid_total == 120
    assert comparison.hard_gate_passed_runs == 3
    assert comparison.baseline_acceptance_ready is True
    assert [run.run_id for run in comparison.runs] == list(APPROVED_RUN_IDS)

    with pytest.raises(BaselineComparisonError, match="three approved runs"):
        compare_baselines(
            _dataset(), candidates[:-1], reports[:-1], observations, reviews
        )


def test_comparison_keeps_invalid_response_visible_and_not_ready(
    tmp_path: Path,
) -> None:
    candidates = _candidates(tmp_path)
    first_attempt = candidates[0].attempts[0]
    invalid_attempt = first_attempt.model_copy(
        update={
            "status": "invalid_response",
            "error_code": "AI_PROVIDER_RESPONSE_INVALID",
            "response_format_valid": False,
            "cited_source_ids": [],
        }
    )
    candidates[0] = BaselineRunFile.model_validate(
        candidates[0].model_copy(
            update={"attempts": [invalid_attempt, *candidates[0].attempts[1:]]}
        ).model_dump(mode="python")
    )
    comparison = _compare(candidates)

    assert comparison.format_valid_total == 119
    assert comparison.hard_gate_passed_runs == 2
    assert comparison.baseline_acceptance_ready is False
    assert comparison.runs[0].format_invalid_case_ids == [first_attempt.case_id]


def test_comparison_rejects_report_metadata_mismatch(tmp_path: Path) -> None:
    candidates = _candidates(tmp_path)
    evidence = {
        candidate.run.run_id: _evidence(candidate) for candidate in candidates
    }
    reports = [evidence[run_id][0] for run_id in APPROVED_RUN_IDS]
    reports[0] = reports[0].model_copy(
        update={
            "run": reports[0].run.model_copy(update={"judge_version": "other-judge-v1"})
        }
    )

    with pytest.raises(BaselineComparisonError, match="does not match"):
        compare_baselines(
            _dataset(),
            candidates,
            reports,
            {run_id: evidence[run_id][1] for run_id in APPROVED_RUN_IDS},
            {run_id: evidence[run_id][2] for run_id in APPROVED_RUN_IDS},
        )


def test_comparison_rejects_tampered_observations_or_report(
    tmp_path: Path,
) -> None:
    candidates = _candidates(tmp_path)
    evidence = {
        candidate.run.run_id: _evidence(candidate) for candidate in candidates
    }
    reports = [evidence[run_id][0] for run_id in APPROVED_RUN_IDS]
    observations = {run_id: evidence[run_id][1] for run_id in APPROVED_RUN_IDS}
    reviews = {run_id: evidence[run_id][2] for run_id in APPROVED_RUN_IDS}
    first = observations["baseline-001"][0]
    observations["baseline-001"] = [
        first.model_copy(update={"groundedness_score": 0.0}),
        *observations["baseline-001"][1:],
    ]

    with pytest.raises(BaselineComparisonError, match="candidates and reviews"):
        compare_baselines(_dataset(), candidates, reports, observations, reviews)

    observations["baseline-001"] = evidence["baseline-001"][1]
    reports[0] = _rehash(
        reports[0].model_copy(
            update={
                "metrics": reports[0].metrics.model_copy(
                    update={"groundedness": 0.0}
                )
            }
        )
    )
    with pytest.raises(BaselineComparisonError, match="deterministic observations"):
        compare_baselines(_dataset(), candidates, reports, observations, reviews)


def test_comparison_writer_is_create_only(tmp_path: Path) -> None:
    candidates = _candidates(tmp_path)
    comparison = _compare(candidates)
    output = tmp_path / "comparison.json"
    write_baseline_comparison(output, comparison)
    original = output.read_bytes()

    with pytest.raises(BaselineComparisonError, match="already exists"):
        write_baseline_comparison(output, comparison)

    assert output.read_bytes() == original
