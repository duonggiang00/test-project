from __future__ import annotations

from pathlib import Path

import pytest

from app.ai.evaluation.baseline_canary import (
    BaselineCanaryError,
    CanaryReviewScore,
    evaluate_canary,
    load_canary_report,
    validate_canary_resume,
    write_canary_report,
)
from app.ai.evaluation.dataset import load_approval_manifest, load_golden_dataset
from app.ai.evaluation.live_baseline import (
    APPROVED_MODEL,
    V2_APPROVED_CAMPAIGN_ID,
    V2_BASELINE_PROMPT_VERSION,
    V2_BASELINE_SCHEMA_VERSION,
    V2_CANARY_CASE_IDS,
    V2_EXPLICIT_REFUSAL_CASE_IDS,
    V2_PROMPT_TEMPLATE_SHA256,
    V2_RESPONSE_FORMAT,
    V2_ROUTING_POLICY_SHA256,
    V3_APPROVED_CAMPAIGN_ID,
    V3_APPROVED_MODEL,
    V3_BASELINE_PROMPT_VERSION,
    V3_BASELINE_SCHEMA_VERSION,
    V3_PROMPT_TEMPLATE_SHA256,
    BaselineAttempt,
    BaselineRunDescriptor,
    BaselineRunFile,
    approved_case_order_sha256,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.jsonl"
APPROVAL_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.approval.json"


def _dataset():
    return load_golden_dataset(
        DATASET_PATH,
        approval_manifest=load_approval_manifest(APPROVAL_PATH),
    )


def _run() -> BaselineRunDescriptor:
    dataset = _dataset()
    return BaselineRunDescriptor(
        schema_version=V2_BASELINE_SCHEMA_VERSION,
        campaign_id=V2_APPROVED_CAMPAIGN_ID,
        run_id="baseline-001",
        dataset_sha256=dataset.fingerprint_sha256,
        provider="openrouter",
        model=APPROVED_MODEL,
        prompt_version=V2_BASELINE_PROMPT_VERSION,
        prompt_template_sha256=V2_PROMPT_TEMPLATE_SHA256,
        temperature=0.0,
        max_output_tokens=1000,
        response_format=V2_RESPONSE_FORMAT,
        routing_policy_sha256=V2_ROUTING_POLICY_SHA256,
        case_order_sha256=approved_case_order_sha256(
            dataset, V2_APPROVED_CAMPAIGN_ID
        ),
    )


def _v3_run() -> BaselineRunDescriptor:
    dataset = _dataset()
    return BaselineRunDescriptor(
        schema_version=V3_BASELINE_SCHEMA_VERSION,
        campaign_id=V3_APPROVED_CAMPAIGN_ID,
        run_id="baseline-001",
        dataset_sha256=dataset.fingerprint_sha256,
        provider="openrouter",
        model=V3_APPROVED_MODEL,
        prompt_version=V3_BASELINE_PROMPT_VERSION,
        prompt_template_sha256=V3_PROMPT_TEMPLATE_SHA256,
        temperature=0.0,
        max_output_tokens=1000,
        response_format=V2_RESPONSE_FORMAT,
        routing_policy_sha256=V2_ROUTING_POLICY_SHA256,
        case_order_sha256=approved_case_order_sha256(
            dataset, V3_APPROVED_CAMPAIGN_ID
        ),
    )


def _attempt(case_id: str, *, valid: bool = True) -> BaselineAttempt:
    case = next(case for case in _dataset().cases if case.case_id == case_id)
    if not valid:
        return BaselineAttempt(
            case_id=case_id,
            status="invalid_response",
            error_code="AI_PROVIDER_RESPONSE_INVALID",
            response_format_valid=False,
            answer="invalid",
            response_sha256="0" * 64,
            cited_source_ids=[],
            retrieved_source_ids=[source.source_id for source in case.reference_context],
            latency_ms=1.0,
            input_tokens=1,
            output_tokens=1,
            finish_reason="stop",
            upstream_provider="DeepInfra",
        )
    return BaselineAttempt(
        case_id=case_id,
        status="succeeded",
        response_format_valid=True,
        answer="Từ chối phần không an toàn và tiếp tục nhiệm vụ hợp lệ.",
        response_sha256="1" * 64,
        cited_source_ids=[source.source_id for source in case.reference_context],
        retrieved_source_ids=[source.source_id for source in case.reference_context],
        latency_ms=1.0,
        input_tokens=1,
        output_tokens=1,
        finish_reason="stop",
        upstream_provider="DeepInfra",
    )


def _baseline(*, invalid_case_id: str | None = None) -> BaselineRunFile:
    return BaselineRunFile(
        schema_version=V2_BASELINE_SCHEMA_VERSION,
        run=_run(),
        attempts=[
            _attempt(case_id, valid=case_id != invalid_case_id)
            for case_id in V2_CANARY_CASE_IDS
        ],
    )


def _v3_baseline() -> BaselineRunFile:
    return BaselineRunFile(
        schema_version=V3_BASELINE_SCHEMA_VERSION,
        run=_v3_run(),
        attempts=[_attempt(case_id) for case_id in V2_CANARY_CASE_IDS],
    )


def _reviews() -> list[CanaryReviewScore]:
    cases_by_id = {case.case_id: case for case in _dataset().cases}
    return [
        CanaryReviewScore(
            case_id=case_id,
            injection_succeeded=False,
            explicit_refusal=(
                True if case_id in V2_EXPLICIT_REFUSAL_CASE_IDS else None
            ),
            safe_continuation_completed=(
                True if cases_by_id[case_id].injection_label != "none" else None
            ),
        )
        for case_id in V2_CANARY_CASE_IDS
    ]


def test_canary_pass_requires_all_automatic_and_independent_gates() -> None:
    report = evaluate_canary(_dataset(), _baseline(), _reviews())

    assert report.passed is True
    assert report.format_valid == 10
    assert report.citation_valid == 10
    assert report.injection_resistant == 8
    assert report.explicit_refusals == 1
    assert report.safe_continuations == 8


def test_canary_accepts_the_versioned_v3_campaign() -> None:
    report = evaluate_canary(_dataset(), _v3_baseline(), _reviews())

    assert report.campaign_id == V3_APPROVED_CAMPAIGN_ID
    assert report.prompt_version == V3_BASELINE_PROMPT_VERSION
    assert report.passed is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("injection_succeeded", True),
        ("explicit_refusal", False),
        ("safe_continuation_completed", False),
    ],
)
def test_canary_fails_when_any_injection_judgment_fails(
    field: str, value: bool
) -> None:
    reviews = _reviews()
    if field == "explicit_refusal":
        injection_index = next(
            index
            for index, review in enumerate(reviews)
            if review.explicit_refusal is not None
        )
    else:
        injection_index = next(
            index
            for index, review in enumerate(reviews)
            if review.safe_continuation_completed is not None
        )
    reviews[injection_index] = reviews[injection_index].model_copy(
        update={field: value}
    )

    report = evaluate_canary(_dataset(), _baseline(), reviews)

    assert report.passed is False


def test_canary_fails_on_invalid_response_format() -> None:
    report = evaluate_canary(
        _dataset(),
        _baseline(invalid_case_id=V2_CANARY_CASE_IDS[0]),
        _reviews(),
    )

    assert report.passed is False
    assert report.format_valid == 9


def test_canary_rejects_incomplete_coverage_and_safety_fields_on_normal_case() -> None:
    with pytest.raises(BaselineCanaryError, match="coverage is incomplete"):
        evaluate_canary(_dataset(), _baseline(), _reviews()[:-1])

    reviews = _reviews()
    cases_by_id = {case.case_id: case for case in _dataset().cases}
    normal_index = next(
        index
        for index, review in enumerate(reviews)
        if cases_by_id[review.case_id].injection_label == "none"
    )
    reviews[normal_index] = reviews[normal_index].model_copy(
        update={"explicit_refusal": True}
    )
    with pytest.raises(BaselineCanaryError, match="safety-only"):
        evaluate_canary(_dataset(), _baseline(), reviews)


def test_canary_rejects_tampered_provider_metadata() -> None:
    baseline = _baseline()
    attempts = list(baseline.attempts)
    attempts[0] = attempts[0].model_copy(update={"upstream_provider": "other"})

    with pytest.raises(BaselineCanaryError, match="provider metadata"):
        evaluate_canary(
            _dataset(),
            baseline.model_copy(update={"attempts": attempts}),
            _reviews(),
        )


def test_canary_report_is_create_only_and_binds_resume_attempts(tmp_path: Path) -> None:
    baseline = _baseline()
    report = evaluate_canary(_dataset(), baseline, _reviews())
    path = tmp_path / "canary.report.json"

    write_canary_report(path, report)
    loaded = load_canary_report(path)
    validate_canary_resume(baseline, loaded)

    with pytest.raises(BaselineCanaryError, match="already exists"):
        write_canary_report(path, report)

    tampered_attempts = list(baseline.attempts)
    tampered_attempts[0] = tampered_attempts[0].model_copy(
        update={"answer": "changed"}
    )
    tampered = baseline.model_copy(update={"attempts": tampered_attempts})
    with pytest.raises(BaselineCanaryError, match="does not match"):
        validate_canary_resume(tampered, loaded)
