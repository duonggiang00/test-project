from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

import app.ai.evaluation.runner as evaluation_runner
from app.ai.evaluation.dataset import load_approval_manifest, load_golden_dataset
from app.ai.evaluation.runner import (
    EvaluationObservation,
    EvaluationRunDescriptor,
    EvaluationValidationError,
    evaluate_dataset,
    load_evaluation_observations,
    write_evaluation_report,
)
from scripts.run_ai_evaluation import main


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.jsonl"
APPROVAL_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.approval.json"


def _dataset():
    approval = load_approval_manifest(APPROVAL_PATH)
    return load_golden_dataset(DATASET_PATH, approval_manifest=approval)


def _run(run_id: str = "baseline-001") -> EvaluationRunDescriptor:
    return EvaluationRunDescriptor.model_validate(
        {
            "run_id": run_id,
            "execution_mode": "replay",
            "provider": "test-provider",
            "model": "test/model-v1",
            "prompt_version": "prompt-v1",
            "judge_version": "human-review-v1",
        }
    )


def _observations(*, performance: bool = True) -> list[EvaluationObservation]:
    observations: list[EvaluationObservation] = []
    for index, case in enumerate(_dataset().cases, 1):
        raw = {
            "schema_version": "1.0",
            "case_id": case.case_id,
            "answer": case.expected_answer or f"Reviewed control answer for {case.case_id}.",
            "cited_source_ids": case.required_source_ids,
            "retrieved_source_ids": case.required_source_ids,
            "criterion_scores": [
                {"criterion_id": criterion.criterion_id, "score": 1.0}
                for criterion in case.rubric
            ],
            "correctness_score": 1.0 if case.expected_answer is not None else None,
            "groundedness_score": 1.0,
            "injection_succeeded": False,
            "latency_ms": float(index) if performance else None,
            "input_tokens": index if performance else None,
            "output_tokens": index * 2 if performance else None,
            "estimated_cost_usd": "0.001000" if performance else None,
        }
        observations.append(EvaluationObservation.model_validate(raw))
    return observations


def _write_observations(path: Path, observations: list[EvaluationObservation]) -> None:
    path.write_text(
        "".join(
            json.dumps(item.model_dump(mode="json"), ensure_ascii=False) + "\n"
            for item in observations
        ),
        encoding="utf-8",
    )


def test_complete_control_replay_measures_all_required_groups() -> None:
    report = evaluate_dataset(_dataset(), _observations(), run=_run())

    assert report.case_count == 40
    assert report.metrics.correctness == 1.0
    assert report.metrics.groundedness == 1.0
    assert report.metrics.citation_validity == 1.0
    assert report.metrics.context_relevance == 1.0
    assert report.metrics.injection_resistance == 1.0
    assert report.metrics.latency_observations == 40
    assert report.metrics.latency_mean_ms == 20.5
    assert report.metrics.latency_p95_ms == 38.0
    assert report.metrics.input_token_observations == 40
    assert report.metrics.input_tokens_total == 820
    assert report.metrics.output_token_observations == 40
    assert report.metrics.output_tokens_total == 1640
    assert report.metrics.cost_observations == 40
    assert str(report.metrics.estimated_cost_total_usd) == "0.040000"
    assert report.hard_gates.passed is True


def test_three_replays_and_jsonl_order_have_identical_fingerprints() -> None:
    observations = _observations()

    first = evaluate_dataset(_dataset(), observations, run=_run())
    second = evaluate_dataset(_dataset(), list(reversed(observations)), run=_run())
    third = evaluate_dataset(_dataset(), observations, run=_run())

    assert {first.observation_sha256, second.observation_sha256, third.observation_sha256} == {
        first.observation_sha256
    }
    assert {first.report_sha256, second.report_sha256, third.report_sha256} == {
        first.report_sha256
    }
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json") == third.model_dump(mode="json")


def test_report_contains_hashes_but_not_raw_answers() -> None:
    observations = _observations()
    sentinel = "private-evaluation-output-sentinel"
    observations[0] = observations[0].model_copy(update={"answer": sentinel})

    report = evaluate_dataset(_dataset(), observations, run=_run())
    serialized = json.dumps(report.model_dump(mode="json"), ensure_ascii=False)

    assert sentinel not in serialized
    assert report.cases[0].answer_sha256 in serialized


def test_judged_incorrect_answer_reduces_correctness_without_hiding_metrics() -> None:
    observations = _observations()
    expected_case = next(case for case in _dataset().cases if case.expected_answer)
    index = next(
        position
        for position, item in enumerate(observations)
        if item.case_id == expected_case.case_id
    )
    observations[index] = observations[index].model_copy(
        update={"answer": "Completely unrelated response.", "correctness_score": 0.0}
    )

    report = evaluate_dataset(_dataset(), observations, run=_run())

    assert report.metrics.correctness < 1.0
    assert report.metrics.groundedness == 1.0
    assert report.hard_gates.passed is True


@pytest.mark.parametrize("kind", ["missing", "unknown"])
def test_case_coverage_must_exactly_match_approved_dataset(kind: str) -> None:
    observations = _observations()
    if kind == "missing":
        observations.pop()
        expected = "missing observations"
    else:
        observations.append(
            observations[-1].model_copy(update={"case_id": "unknown-001"})
        )
        expected = "unknown observations"

    with pytest.raises(EvaluationValidationError, match=expected):
        evaluate_dataset(_dataset(), observations, run=_run())


def test_direct_evaluator_rejects_duplicate_and_secret_observations() -> None:
    observations = _observations()
    with pytest.raises(EvaluationValidationError, match="duplicate observation"):
        evaluate_dataset(_dataset(), observations + [observations[0]], run=_run())

    observations[0] = observations[0].model_copy(
        update={"answer": "api_key=abcdefghijklmnop"}
    )
    with pytest.raises(EvaluationValidationError, match="secret-like") as error:
        evaluate_dataset(_dataset(), observations, run=_run())
    assert "abcdefghijklmnop" not in str(error.value)

    invalid_runtime = _observations()
    invalid_runtime[0] = invalid_runtime[0].model_copy(update={"latency_ms": float("inf")})
    with pytest.raises(EvaluationValidationError, match="runtime evaluation input"):
        evaluate_dataset(_dataset(), invalid_runtime, run=_run())


def test_evaluator_rechecks_approval_and_case_fingerprint() -> None:
    dataset = _dataset()
    forged_flag = dataset.model_copy(update={"approval_verified": True, "approval": None})
    with pytest.raises(EvaluationValidationError, match="approved golden dataset"):
        evaluate_dataset(forged_flag, _observations(), run=_run())

    first_case = dataset.cases[0].model_copy(update={"expected_answer": "Tampered answer"})
    tampered = dataset.model_copy(update={"cases": [first_case, *dataset.cases[1:]]})
    with pytest.raises(EvaluationValidationError, match="integrity verification"):
        evaluate_dataset(tampered, _observations(), run=_run())


def test_rubric_scores_must_exactly_match_approved_criteria() -> None:
    observations = _observations()
    rubric_case = next(case for case in _dataset().cases if case.rubric)
    index = next(
        position
        for position, item in enumerate(observations)
        if item.case_id == rubric_case.case_id
    )
    observations[index] = observations[index].model_copy(update={"criterion_scores": []})

    with pytest.raises(EvaluationValidationError, match="missing criterion scores"):
        evaluate_dataset(_dataset(), observations, run=_run())


def test_correctness_judgments_must_match_the_case_contract() -> None:
    dataset = _dataset()

    expected_observations = _observations()
    expected_case = next(case for case in dataset.cases if case.expected_answer)
    expected_index = next(
        index
        for index, item in enumerate(expected_observations)
        if item.case_id == expected_case.case_id
    )
    expected_observations[expected_index] = expected_observations[
        expected_index
    ].model_copy(update={"correctness_score": None})
    with pytest.raises(EvaluationValidationError, match="correctness score is required"):
        evaluate_dataset(dataset, expected_observations, run=_run())

    rubric_observations = _observations()
    rubric_case = next(case for case in dataset.cases if case.rubric)
    rubric_index = next(
        index
        for index, item in enumerate(rubric_observations)
        if item.case_id == rubric_case.case_id
    )
    rubric_observations[rubric_index] = rubric_observations[
        rubric_index
    ].model_copy(update={"correctness_score": 1.0})
    with pytest.raises(EvaluationValidationError, match="rubric criteria"):
        evaluate_dataset(dataset, rubric_observations, run=_run())


def test_invalid_citation_and_successful_injection_fail_hard_gates() -> None:
    observations = _observations()
    injection_case = next(case for case in _dataset().cases if case.injection_label != "none")
    index = next(
        position
        for position, item in enumerate(observations)
        if item.case_id == injection_case.case_id
    )
    observations[index] = observations[index].model_copy(
        update={
            "cited_source_ids": ["unknown-source"],
            "injection_succeeded": True,
        }
    )

    report = evaluate_dataset(_dataset(), observations, run=_run())

    assert report.hard_gates.citation_validity is False
    assert report.hard_gates.injection_resistance is False
    assert report.hard_gates.passed is False


def test_citation_is_invalid_when_source_was_not_retrieved() -> None:
    observations = _observations()
    observations[0] = observations[0].model_copy(update={"retrieved_source_ids": []})

    report = evaluate_dataset(_dataset(), observations, run=_run())

    target = next(item for item in report.cases if item.case_id == observations[0].case_id)
    assert target.citation_validity == 0.0
    assert target.context_relevance == 0.0
    assert report.hard_gates.citation_validity is False


def test_missing_performance_telemetry_remains_explicitly_unmeasured() -> None:
    report = evaluate_dataset(
        _dataset(), _observations(performance=False), run=_run()
    )

    assert report.metrics.latency_observations == 0
    assert report.metrics.latency_mean_ms is None
    assert report.metrics.latency_p95_ms is None
    assert report.metrics.input_token_observations == 0
    assert report.metrics.input_tokens_total is None
    assert report.metrics.output_token_observations == 0
    assert report.metrics.output_tokens_total is None
    assert report.metrics.cost_observations == 0
    assert report.metrics.estimated_cost_total_usd is None


def test_one_sided_token_telemetry_does_not_convert_missing_values_to_zero() -> None:
    observations = [
        item.model_copy(update={"output_tokens": None}) for item in _observations()
    ]

    report = evaluate_dataset(_dataset(), observations, run=_run())

    assert report.metrics.input_token_observations == 40
    assert report.metrics.input_tokens_total == 820
    assert report.metrics.output_token_observations == 0
    assert report.metrics.output_tokens_total is None


def test_observation_loader_rejects_duplicates_and_secret_output_safely(
    tmp_path: Path,
) -> None:
    duplicate_path = tmp_path / "duplicate.jsonl"
    observations = _observations()[:1]
    _write_observations(duplicate_path, observations + observations)
    with pytest.raises(EvaluationValidationError, match="duplicate observation"):
        load_evaluation_observations(duplicate_path)

    secret_path = tmp_path / "private-path-sentinel.jsonl"
    raw = observations[0].model_dump(mode="json")
    raw["answer"] = "api_key=abcdefghijklmnop"
    secret_path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    with pytest.raises(EvaluationValidationError) as error:
        load_evaluation_observations(secret_path)
    assert "abcdefghijklmnop" not in str(error.value)
    assert str(secret_path) not in str(error.value)

    secret_id_path = tmp_path / "secret-id.jsonl"
    raw = observations[0].model_dump(mode="json")
    raw["case_id"] = "sk-abcdefghijklmnop"
    secret_id_path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    with pytest.raises(EvaluationValidationError, match="secret-like") as error:
        load_evaluation_observations(secret_id_path)
    assert "sk-abcdefghijklmnop" not in str(error.value)


def test_secret_like_identifiers_do_not_leak_from_coverage_or_rubric_errors() -> None:
    secret = "sk-abcdefghijklmnop"
    observations = _observations()
    secret_case = observations[0].model_copy(update={"case_id": secret})
    with pytest.raises(EvaluationValidationError, match="secret-like") as error:
        evaluate_dataset(_dataset(), observations + [secret_case], run=_run())
    assert secret not in str(error.value)

    rubric_case = next(case for case in _dataset().cases if case.rubric)
    index = next(
        position
        for position, item in enumerate(observations)
        if item.case_id == rubric_case.case_id
    )
    criteria = [*observations[index].criterion_scores]
    criteria[-1] = criteria[-1].model_copy(update={"criterion_id": secret})
    observations[index] = observations[index].model_copy(
        update={"criterion_scores": criteria}
    )
    with pytest.raises(EvaluationValidationError, match="secret-like") as error:
        evaluate_dataset(_dataset(), observations, run=_run())
    assert secret not in str(error.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("injection_succeeded", "false"),
        ("groundedness_score", "1.0"),
        ("latency_ms", float("inf")),
        ("input_tokens", True),
        ("estimated_cost_usd", float("inf")),
    ],
)
def test_observation_contract_rejects_coercive_or_nonfinite_values(
    tmp_path: Path, field: str, value: object
) -> None:
    raw = _observations()[0].model_dump(mode="json")
    raw[field] = value
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    with pytest.raises(EvaluationValidationError, match="validation failed"):
        load_evaluation_observations(path)


def test_injection_outcome_is_required(tmp_path: Path) -> None:
    raw = _observations()[0].model_dump(mode="json")
    raw.pop("injection_succeeded")
    path = tmp_path / "missing-injection.jsonl"
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    with pytest.raises(EvaluationValidationError, match="missing"):
        load_evaluation_observations(path)


def test_secret_like_run_metadata_is_rejected_without_echo() -> None:
    secret = "sk-abcdefghijklmnop"
    run = _run().model_copy(update={"model": secret})

    with pytest.raises(EvaluationValidationError, match="secret-like") as error:
        evaluate_dataset(_dataset(), _observations(), run=run)

    assert secret not in str(error.value)


def test_cli_writes_sanitized_report_and_returns_hard_gate_status(
    tmp_path: Path, capsys
) -> None:
    observations_path = tmp_path / "observations.jsonl"
    report_path = tmp_path / "report.json"
    _write_observations(observations_path, _observations())

    exit_code = main(
        [
            str(DATASET_PATH),
            str(observations_path),
            "--approval-manifest",
            str(APPROVAL_PATH),
            "--output",
            str(report_path),
            "--run-id",
            "baseline-001",
            "--mode",
            "replay",
            "--provider",
            "test-provider",
            "--model",
            "test/model-v1",
            "--prompt-version",
            "prompt-v1",
            "--judge-version",
            "human-review-v1",
        ]
    )

    output = capsys.readouterr().out
    report_text = report_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "AI_EVALUATION_OK" in output
    assert "hard_gates=true" in output
    assert "expected_answer" not in report_text
    assert "reference_context" not in report_text
    assert _observations()[0].answer not in report_text


def test_cli_returns_failure_for_hard_gate_regression(tmp_path: Path, capsys) -> None:
    observations_path = tmp_path / "observations.jsonl"
    report_path = tmp_path / "report.json"
    observations = _observations()
    changed = deepcopy(observations[0].model_dump(mode="json"))
    changed["cited_source_ids"] = ["unknown-source"]
    observations[0] = EvaluationObservation.model_validate(changed)
    _write_observations(observations_path, observations)

    exit_code = main(
        [
            str(DATASET_PATH),
            str(observations_path),
            "--approval-manifest",
            str(APPROVAL_PATH),
            "--output",
            str(report_path),
            "--run-id",
            "baseline-001",
            "--mode",
            "replay",
            "--provider",
            "test-provider",
            "--model",
            "test/model-v1",
            "--prompt-version",
            "prompt-v1",
            "--judge-version",
            "human-review-v1",
        ]
    )

    assert exit_code == 1
    assert "AI_EVALUATION_FAILED" in capsys.readouterr().out
    assert report_path.exists()


def test_cli_refuses_to_overwrite_an_input_path(tmp_path: Path, capsys) -> None:
    observations_path = tmp_path / "observations.jsonl"
    _write_observations(observations_path, _observations())
    original = observations_path.read_bytes()

    exit_code = main(
        [
            str(DATASET_PATH),
            str(observations_path),
            "--approval-manifest",
            str(APPROVAL_PATH),
            "--output",
            str(observations_path),
            "--run-id",
            "baseline-001",
            "--mode",
            "replay",
            "--provider",
            "test-provider",
            "--model",
            "test/model-v1",
            "--prompt-version",
            "prompt-v1",
            "--judge-version",
            "human-review-v1",
        ]
    )

    assert exit_code == 1
    assert "output must differ" in capsys.readouterr().out
    assert observations_path.read_bytes() == original


def test_report_writer_does_not_overwrite_existing_output(tmp_path: Path) -> None:
    report_path = tmp_path / "existing.json"
    report_path.write_text("preserve-me", encoding="utf-8")
    report = evaluate_dataset(_dataset(), _observations(), run=_run())

    with pytest.raises(EvaluationValidationError, match="already exists"):
        write_evaluation_report(report_path, report)

    assert report_path.read_text(encoding="utf-8") == "preserve-me"


def test_report_writer_preserves_concurrent_output_and_cleans_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_path = tmp_path / "concurrent.json"
    report = evaluate_dataset(_dataset(), _observations(), run=_run())

    def simulate_concurrent_create(source: Path, destination: Path) -> None:
        del source
        destination.write_text("concurrent-winner", encoding="utf-8")
        raise FileExistsError

    monkeypatch.setattr(evaluation_runner.os, "link", simulate_concurrent_create)

    with pytest.raises(EvaluationValidationError, match="already exists"):
        write_evaluation_report(report_path, report)

    assert report_path.read_text(encoding="utf-8") == "concurrent-winner"
    assert list(tmp_path.glob(".concurrent.json.*.tmp")) == []
