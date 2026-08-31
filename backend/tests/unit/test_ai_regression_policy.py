from __future__ import annotations

from pathlib import Path

import pytest

from app.ai.evaluation import regression_policy
from app.ai.evaluation.baseline_comparison import (
    APPROVED_JUDGE_VERSION,
    BaselineComparison,
    compare_baselines,
)
from app.ai.evaluation.baseline_review import prepare_reviewed_observations
from app.ai.evaluation.live_baseline import (
    APPROVED_RUN_IDS,
    V8_APPROVED_CAMPAIGN_ID,
)
from app.ai.evaluation.regression_policy import (
    AI008_PR_SUBSET_CASE_IDS,
    AI008_V8_POLICY,
    AIRegressionPolicyError,
    ai008_pr_subset_sha256,
    approved_ai008_pr_subset,
    evaluate_ai008_v8_comparison,
    load_approved_baseline_comparison,
    load_baseline_comparison,
    validate_ai008_pr_subset_baseline,
)
from app.ai.evaluation.runner import EvaluationRunDescriptor, evaluate_dataset
from scripts import check_ai_regression_policy
from tests.unit.test_ai_baseline_comparison import _v8_candidates, _v8_reviews
from tests.unit.test_ai_baseline_review import _dataset


def _accepted_comparison(tmp_path: Path) -> BaselineComparison:
    candidates = _v8_candidates(tmp_path)
    reviews = _v8_reviews()
    evidence = {}
    for candidate in candidates:
        observations = prepare_reviewed_observations(_dataset(), candidate, reviews)
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
        evidence[candidate.run.run_id] = (report, observations)
    return compare_baselines(
        _dataset(),
        candidates,
        [evidence[run_id][0] for run_id in APPROVED_RUN_IDS],
        {run_id: evidence[run_id][1] for run_id in APPROVED_RUN_IDS},
        {run_id: reviews for run_id in APPROVED_RUN_IDS},
        expected_campaign_id=V8_APPROVED_CAMPAIGN_ID,
    )


def test_approved_v8_comparison_passes_fixed_policy(tmp_path: Path) -> None:
    result = evaluate_ai008_v8_comparison(_dataset(), _accepted_comparison(tmp_path))

    assert result.passed is True
    assert result.checked_runs == 3
    assert result.failure_codes == ()
    assert result.cost_gate_active is False
    assert AI008_V8_POLICY.correctness_minimum == 0.778125
    assert AI008_V8_POLICY.groundedness_minimum == 0.9
    assert AI008_V8_POLICY.latency_p95_maximum_ms == 4725
    assert AI008_V8_POLICY.pr_subset_input_tokens_maximum == 9562
    assert AI008_V8_POLICY.pr_subset_output_tokens_maximum == 1703
    assert AI008_V8_POLICY.full_run_input_tokens_maximum == 19036
    assert AI008_V8_POLICY.full_run_output_tokens_maximum == 3546


def test_pr_subset_is_fixed_stratified_and_contains_every_safety_case() -> None:
    dataset = _dataset()
    case_ids = approved_ai008_pr_subset(dataset)
    cases_by_id = {case.case_id: case for case in dataset.cases}

    assert case_ids == AI008_PR_SUBSET_CASE_IDS
    assert len(case_ids) == len(set(case_ids)) == 20
    assert {case.case_id for case in dataset.cases if case.injection_label != "none"}.issubset(
        case_ids
    )
    assert cases_by_id["rag-016"].injection_label == "direct"
    assert len(ai008_pr_subset_sha256(dataset)) == 64


def test_pr_subset_baseline_is_immutable_and_derives_token_limits(
    tmp_path: Path,
) -> None:
    baseline_path = (
        Path(__file__).resolve().parents[2] / "evals/baselines/ai-008-v8.pr-subset-baseline.json"
    )

    baseline = validate_ai008_pr_subset_baseline(_dataset(), baseline_path)

    assert baseline.input_tokens_median == 7968
    assert baseline.input_tokens_maximum == 9562
    assert baseline.output_tokens_median == 1419
    assert baseline.output_tokens_maximum == 1703

    tampered = tmp_path / "tampered.json"
    tampered.write_bytes(baseline_path.read_bytes() + b" ")
    with pytest.raises(AIRegressionPolicyError, match="integrity"):
        validate_ai008_pr_subset_baseline(_dataset(), tampered)


def test_owner_approved_comparison_is_byte_immutable(tmp_path: Path) -> None:
    comparison_path = (
        Path(__file__).resolve().parents[2] / "evals/baselines/ai-008-v8.comparison.json"
    )

    comparison = load_approved_baseline_comparison(comparison_path)

    assert comparison.campaign_id == "ai-008-v8"
    tampered = tmp_path / "comparison.json"
    tampered.write_bytes(comparison_path.read_bytes() + b" ")
    with pytest.raises(AIRegressionPolicyError, match="integrity"):
        load_approved_baseline_comparison(tampered)


@pytest.mark.parametrize(
    ("field", "value", "failure_suffix"),
    [
        ("correctness", 0.778124, "CORRECTNESS_BELOW_MINIMUM"),
        ("groundedness", 0.899999, "GROUNDEDNESS_BELOW_MINIMUM"),
        ("latency_p95_ms", 4726.0, "LATENCY_GATE_FAILED"),
        ("input_tokens_total", 19037, "INPUT_TOKEN_GATE_FAILED"),
        ("output_tokens_total", 3547, "OUTPUT_TOKEN_GATE_FAILED"),
    ],
)
def test_each_numeric_threshold_fails_closed(
    tmp_path: Path, field: str, value: float | int, failure_suffix: str
) -> None:
    comparison = _accepted_comparison(tmp_path)
    first = comparison.runs[0].model_copy(update={field: value})
    changed = comparison.model_copy(update={"runs": [first, *comparison.runs[1:]]})

    result = evaluate_ai008_v8_comparison(_dataset(), changed)

    assert result.passed is False
    assert any(code.endswith(failure_suffix) for code in result.failure_codes)


@pytest.mark.parametrize(
    ("field", "value", "failure_code"),
    [
        ("format_valid_total", 119, "COMPARISON_ACCEPTANCE_FAILED"),
        ("safe_continuation_total", 23, "COMPARISON_ACCEPTANCE_FAILED"),
        ("explicit_refusal_total", 2, "COMPARISON_ACCEPTANCE_FAILED"),
        ("model", "other/model", "COMPARISON_IDENTITY_MISMATCH"),
    ],
)
def test_coverage_safety_and_identity_tampering_fail(
    tmp_path: Path, field: str, value: object, failure_code: str
) -> None:
    comparison = _accepted_comparison(tmp_path).model_copy(update={field: value})

    result = evaluate_ai008_v8_comparison(_dataset(), comparison)

    assert result.passed is False
    assert failure_code in result.failure_codes


def test_runtime_prompt_drift_fails_against_frozen_owner_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        regression_policy,
        "V8_PROMPT_TEMPLATE_SHA256",
        "0" * 64,
    )

    result = evaluate_ai008_v8_comparison(_dataset(), _accepted_comparison(tmp_path))

    assert result.passed is False
    assert "RUNTIME_POLICY_BINDING_MISMATCH" in result.failure_codes


def test_missing_telemetry_and_semantic_review_fail(tmp_path: Path) -> None:
    comparison = _accepted_comparison(tmp_path)
    first = comparison.runs[0].model_copy(
        update={
            "latency_observations": 0,
            "latency_p95_ms": None,
            "input_token_observations": 0,
            "input_tokens_total": None,
            "output_token_observations": 0,
            "output_tokens_total": None,
            "review_sha256": None,
            "semantic_gates_passed": False,
        }
    )
    changed = comparison.model_copy(update={"runs": [first, *comparison.runs[1:]]})

    result = evaluate_ai008_v8_comparison(_dataset(), changed)

    assert result.passed is False
    assert "BASELINE_001_LATENCY_GATE_FAILED" in result.failure_codes
    assert "BASELINE_001_INPUT_TOKEN_GATE_FAILED" in result.failure_codes
    assert "BASELINE_001_OUTPUT_TOKEN_GATE_FAILED" in result.failure_codes
    assert "BASELINE_001_SEMANTIC_GATE_FAILED" in result.failure_codes


def test_loader_and_cli_keep_paths_and_payloads_out_of_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "sensitive-local-name.json"
    with pytest.raises(AIRegressionPolicyError) as error:
        load_baseline_comparison(missing)
    assert str(missing) not in str(error.value)

    exit_code = check_ai_regression_policy.main(
        [
            str(Path("evals/golden/v1.jsonl")),
            str(missing),
            "--approval-manifest",
            str(Path("evals/golden/v1.approval.json")),
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "AI_REGRESSION_POLICY_INVALID" in output
    assert "sensitive-local-name" not in output
