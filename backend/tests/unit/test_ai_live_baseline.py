from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import app.ai.evaluation.live_baseline as live_baseline
import scripts.run_ai_live_baseline as live_baseline_cli
from app.ai.evaluation.baseline_canary import (
    CanaryReviewScore,
    evaluate_canary,
    write_canary_report,
)
from app.ai.evaluation.baseline_comparison import APPROVED_JUDGE_VERSION
from app.ai.evaluation.baseline_review import (
    BaselineReviewScore,
    prepare_reviewed_observations,
    write_reviewed_observations,
)
from app.ai.evaluation.dataset import (
    golden_dataset_fingerprint,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.live_baseline import (
    BASELINE_PROMPT_VERSION,
    BASELINE_SCHEMA_VERSION,
    APPROVED_MODEL,
    APPROVED_RUN_IDS,
    PROMPT_TEMPLATE_SHA256,
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
    V4_APPROVED_CAMPAIGN_ID,
    V4_APPROVED_MODEL,
    V4_BASELINE_PROMPT_VERSION,
    V4_BASELINE_SCHEMA_VERSION,
    V4_PROMPT_TEMPLATE_SHA256,
    V4_RESPONSE_PARSE_MODE,
    BaselineProviderFailure,
    BaselineAttempt,
    BaselineCampaignFile,
    BaselineRunDescriptor,
    BaselineResponseFailure,
    BaselineValidationError,
    _collect_live_baseline,
    approved_case_order_sha256,
    build_candidate_messages,
    load_baseline_run,
    parse_candidate_response,
)
from app.ai.provider import (
    AIProviderError,
    GenerateRequest,
    GenerateResult,
    ProviderExecutionBinding,
    TokenUsage,
)
from app.ai.evaluation.runner import (
    EvaluationRunDescriptor,
    evaluate_dataset,
    write_evaluation_report,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.jsonl"
APPROVAL_PATH = BACKEND_ROOT / "evals" / "golden" / "v1.approval.json"


def _dataset():
    return load_golden_dataset(
        DATASET_PATH,
        approval_manifest=load_approval_manifest(APPROVAL_PATH),
    )


def _run(run_id: str = "baseline-001", **updates) -> BaselineRunDescriptor:
    values = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "campaign_id": "ai-008-v1",
        "run_id": run_id,
        "dataset_sha256": _dataset().fingerprint_sha256,
        "provider": "openrouter",
        "model": APPROVED_MODEL,
        "prompt_version": BASELINE_PROMPT_VERSION,
        "prompt_template_sha256": PROMPT_TEMPLATE_SHA256,
        "temperature": 0.0,
        "max_output_tokens": 1000,
    }
    values.update(updates)
    return BaselineRunDescriptor.model_validate(values)


def _v2_run(run_id: str = "baseline-001", **updates) -> BaselineRunDescriptor:
    dataset = _dataset()
    values = {
        "schema_version": V2_BASELINE_SCHEMA_VERSION,
        "campaign_id": V2_APPROVED_CAMPAIGN_ID,
        "run_id": run_id,
        "dataset_sha256": dataset.fingerprint_sha256,
        "provider": "openrouter",
        "model": APPROVED_MODEL,
        "prompt_version": V2_BASELINE_PROMPT_VERSION,
        "prompt_template_sha256": V2_PROMPT_TEMPLATE_SHA256,
        "temperature": 0.0,
        "max_output_tokens": 1000,
        "response_format": V2_RESPONSE_FORMAT,
        "routing_policy_sha256": V2_ROUTING_POLICY_SHA256,
        "case_order_sha256": approved_case_order_sha256(
            dataset, V2_APPROVED_CAMPAIGN_ID
        ),
    }
    values.update(updates)
    return BaselineRunDescriptor.model_validate(values)


def _v3_run(run_id: str = "baseline-001", **updates) -> BaselineRunDescriptor:
    dataset = _dataset()
    values = {
        "schema_version": V3_BASELINE_SCHEMA_VERSION,
        "campaign_id": V3_APPROVED_CAMPAIGN_ID,
        "run_id": run_id,
        "dataset_sha256": dataset.fingerprint_sha256,
        "provider": "openrouter",
        "model": V3_APPROVED_MODEL,
        "prompt_version": V3_BASELINE_PROMPT_VERSION,
        "prompt_template_sha256": V3_PROMPT_TEMPLATE_SHA256,
        "temperature": 0.0,
        "max_output_tokens": 1000,
        "response_format": V2_RESPONSE_FORMAT,
        "routing_policy_sha256": V2_ROUTING_POLICY_SHA256,
        "case_order_sha256": approved_case_order_sha256(
            dataset, V3_APPROVED_CAMPAIGN_ID
        ),
    }
    values.update(updates)
    return BaselineRunDescriptor.model_validate(values)


def _v4_run(run_id: str = "baseline-001", **updates) -> BaselineRunDescriptor:
    dataset = _dataset()
    values = {
        "schema_version": V4_BASELINE_SCHEMA_VERSION,
        "campaign_id": V4_APPROVED_CAMPAIGN_ID,
        "run_id": run_id,
        "dataset_sha256": dataset.fingerprint_sha256,
        "provider": "openrouter",
        "model": V4_APPROVED_MODEL,
        "prompt_version": V4_BASELINE_PROMPT_VERSION,
        "prompt_template_sha256": V4_PROMPT_TEMPLATE_SHA256,
        "temperature": 0.0,
        "max_output_tokens": 1000,
        "response_format": V2_RESPONSE_FORMAT,
        "routing_policy_sha256": V2_ROUTING_POLICY_SHA256,
        "case_order_sha256": approved_case_order_sha256(
            dataset, V4_APPROVED_CAMPAIGN_ID
        ),
        "response_parse_mode": V4_RESPONSE_PARSE_MODE,
    }
    values.update(updates)
    return BaselineRunDescriptor.model_validate(values)


def _canary_reviews() -> list[CanaryReviewScore]:
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


def _full_reviews() -> list[BaselineReviewScore]:
    return [
        BaselineReviewScore(
            case_id=case.case_id,
            criterion_scores=[
                {"criterion_id": criterion.criterion_id, "score": 1.0}
                for criterion in case.rubric
            ],
            correctness_score=1.0 if case.expected_answer is not None else None,
            groundedness_score=1.0,
            injection_succeeded=False,
        )
        for case in _dataset().cases
    ]


def test_successful_attempt_requires_format_valid_flag() -> None:
    with pytest.raises(ValueError, match="format-valid"):
        BaselineAttempt.model_validate(
            {
                "case_id": "rag-001",
                "status": "succeeded",
                "response_format_valid": False,
                "answer": "candidate",
                "response_sha256": "0" * 64,
                "cited_source_ids": ["source-001"],
                "retrieved_source_ids": ["source-001"],
                "latency_ms": 1.0,
                "input_tokens": 1,
                "output_tokens": 1,
                "estimated_cost_usd": None,
            }
        )


@dataclass
class FakeProvider:
    error: AIProviderError | None = None
    raw_text: str | None = None
    finish_reason: str = "stop"
    provider_variant: str | None = None
    execution_binding: ProviderExecutionBinding | None = field(
        default_factory=lambda: ProviderExecutionBinding(
            max_retries=0,
            routing_policy_sha256=V2_ROUTING_POLICY_SHA256,
        )
    )
    requests: list[GenerateRequest] = field(default_factory=list)

    def generate(self, request: GenerateRequest) -> GenerateResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        payload = json.loads(request.messages[-1]["content"])
        source_ids = [source["source_id"] for source in payload["sources"]]
        text = self.raw_text
        if text is None:
            text = json.dumps(
                {
                    "answer": "Câu trả lời kiểm soát.",
                    "cited_source_ids": source_ids,
                },
                ensure_ascii=False,
            )
        return GenerateResult(
            text=text,
            tool_calls=None,
            provider="openrouter",
            model=request.model,
            usage=TokenUsage(input_tokens=20, output_tokens=10),
            latency_ms=12.5,
            finish_reason=self.finish_reason,
            provider_variant=self.provider_variant,
        )

    async def stream(self, request):  # pragma: no cover - protocol-only stub
        del request
        if False:
            yield


def test_candidate_prompt_is_deterministic_and_separates_untrusted_sources() -> None:
    case = _dataset().cases[0]

    first = build_candidate_messages(case)
    second = build_candidate_messages(case)

    assert first == second
    assert first[0]["role"] == "system"
    assert "untrusted data" in first[0]["content"]
    payload = json.loads(first[1]["content"])
    assert payload["task"] == case.input
    assert payload["sources"][0]["source_id"] == case.reference_context[0].source_id


def test_v2_prompt_is_deterministic_and_requires_refusal_plus_safe_continuation() -> None:
    case = next(case for case in _dataset().cases if case.case_id == "rag-016")

    first = build_candidate_messages(case, prompt_version=V2_BASELINE_PROMPT_VERSION)
    second = build_candidate_messages(case, prompt_version=V2_BASELINE_PROMPT_VERSION)

    assert first == second
    system = first[0]["content"]
    assert "explicit Vietnamese refusal" in system
    assert "continue the legitimate educational part" in system
    assert "placeholder" in system
    payload = json.loads(first[1]["content"])
    assert payload["task"] == case.input
    assert payload["sources"]


def test_v3_prompt_requires_silent_indirect_rejection_and_safe_completion() -> None:
    case = next(case for case in _dataset().cases if case.case_id == "rag-016")

    messages = build_candidate_messages(
        case, prompt_version=V3_BASELINE_PROMPT_VERSION
    )

    system = messages[0]["content"]
    assert "ignore them silently" in system
    assert "refuse only that unsafe clause" in system
    assert "A refusal alone is incomplete" in system
    assert "complete every safe requirement" in system
    assert json.loads(messages[1]["content"])["task"] == case.input


def test_v4_parser_extracts_only_one_json_payload_before_strict_validation() -> None:
    payload = json.dumps(
        {"answer": "Câu trả lời kiểm soát.", "cited_source_ids": ["source-001"]},
        ensure_ascii=False,
    )
    raw = "Nhận xét ngoài envelope.\n" + payload

    assert parse_candidate_response(raw) == (raw, [], False)
    assert parse_candidate_response(raw, allow_extraction=True) == (
        "Câu trả lời kiểm soát.",
        ["source-001"],
        True,
    )
    assert (
        parse_candidate_response(
            "```json\n" + payload + "\n```\n```json\n" + payload + "\n```",
            allow_extraction=True,
        )
        == ("```json\n" + payload + "\n```\n```json\n" + payload + "\n```", [], False)
    )
    mixed = "```json\n" + payload + "\n```\n" + payload
    assert parse_candidate_response(mixed, allow_extraction=True) == (mixed, [], False)


def test_v4_collection_uses_extraction_mode_and_preserves_raw_hash(tmp_path: Path) -> None:
    payload = json.dumps(
        {"answer": "Câu trả lời kiểm soát.", "cited_source_ids": ["source-001"]},
        ensure_ascii=False,
    )
    raw = "Nhận xét ngoài envelope.\n" + payload
    provider = FakeProvider(raw_text=raw, provider_variant="DeepInfra")

    state = _collect_live_baseline(
        _dataset(),
        output_path=tmp_path / "baseline-001.candidates.json",
        budget_path=tmp_path / "campaign.json",
        run=_v4_run(),
        provider=provider,
        max_new_calls=1,
    )

    attempt = state.attempts[0]
    assert attempt.status == "succeeded"
    assert attempt.answer == "Câu trả lời kiểm soát."
    assert attempt.response_sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    raw_evidence = tmp_path / "baseline-001.candidates.raw.jsonl"
    assert json.loads(raw_evidence.read_text(encoding="utf-8"))["raw_response"] == raw


def test_legacy_run_storage_omits_v4_parse_metadata(tmp_path: Path) -> None:
    _collect_live_baseline(
        _dataset(),
        output_path=tmp_path / "baseline-001.candidates.json",
        budget_path=tmp_path / "campaign.json",
        run=_run(),
        provider=FakeProvider(),
        max_new_calls=1,
    )
    saved_run = json.loads(
        (tmp_path / "baseline-001.candidates.json").read_text(encoding="utf-8")
    )
    saved_campaign = json.loads(
        (tmp_path / "campaign.json").read_text(encoding="utf-8")
    )
    assert "response_parse_mode" not in saved_run["run"]
    assert "response_parse_mode" not in saved_campaign


def test_v3_collection_reuses_the_ten_case_fail_closed_canary(tmp_path: Path) -> None:
    provider = FakeProvider(provider_variant="DeepInfra")

    state = _collect_live_baseline(
        _dataset(),
        output_path=tmp_path / "baseline-001.candidates.json",
        budget_path=tmp_path / "campaign.json",
        run=_v3_run(),
        provider=provider,
        max_new_calls=10,
    )

    assert len(state.attempts) == 10
    assert all(request.model == V3_APPROVED_MODEL for request in provider.requests)
    assert all(request.max_tokens == 1000 for request in provider.requests)
    assert all(request.response_format == "json_object" for request in provider.requests)

    blocked = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="passing canary"):
        _collect_live_baseline(
            _dataset(),
            output_path=tmp_path / "baseline-001.candidates.json",
            budget_path=tmp_path / "campaign.json",
            run=_v3_run(),
            provider=blocked,
            max_new_calls=1,
        )
    assert blocked.requests == []


def test_v3_rejects_wrong_model_before_reserving_or_calling(tmp_path: Path) -> None:
    provider = FakeProvider(provider_variant="DeepInfra")

    with pytest.raises(BaselineValidationError, match="approved campaign"):
        _collect_live_baseline(
            _dataset(),
            output_path=tmp_path / "baseline-001.candidates.json",
            budget_path=tmp_path / "campaign.json",
            run=_v3_run(model=APPROVED_MODEL),
            provider=provider,
            max_new_calls=1,
        )

    assert provider.requests == []
    assert list(tmp_path.iterdir()) == []


def test_v3_invalid_response_permanently_blocks_resume(tmp_path: Path) -> None:
    output = tmp_path / "baseline-001.candidates.json"
    budget = tmp_path / "campaign.json"
    invalid_provider = FakeProvider(
        raw_text="not-json", provider_variant="DeepInfra"
    )

    with pytest.raises(BaselineResponseFailure, match="strict envelope"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_v3_run(),
            provider=invalid_provider,
            max_new_calls=1,
        )

    resume_provider = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="resume is disabled"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_v3_run(),
            provider=resume_provider,
            max_new_calls=9,
        )

    assert resume_provider.requests == []
    assert len(load_baseline_run(output).attempts) == 1


def test_v3_requires_passing_prior_run_evidence_before_run_two(
    tmp_path: Path,
) -> None:
    dataset = _dataset()
    output = tmp_path / "baseline-001.candidates.json"
    budget = tmp_path / "campaign.json"
    first = _collect_live_baseline(
        dataset,
        output_path=output,
        budget_path=budget,
        run=_v3_run(),
        provider=FakeProvider(provider_variant="DeepInfra"),
        max_new_calls=10,
    )
    canary_reviews = _canary_reviews()
    write_canary_report(
        tmp_path / "baseline-001.canary.report.json",
        evaluate_canary(dataset, first, canary_reviews),
    )
    (tmp_path / "baseline-001.canary.review.jsonl").write_text(
        "\n".join(review.model_dump_json() for review in canary_reviews) + "\n",
        encoding="utf-8",
    )

    blocked_provider = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="prior-run evidence"):
        _collect_live_baseline(
            dataset,
            output_path=tmp_path / "baseline-002.candidates.json",
            budget_path=budget,
            run=_v3_run(run_id="baseline-002"),
            provider=blocked_provider,
            max_new_calls=1,
        )
    assert blocked_provider.requests == []

    first = _collect_live_baseline(
        dataset,
        output_path=output,
        budget_path=budget,
        run=_v3_run(),
        provider=FakeProvider(provider_variant="DeepInfra"),
        max_new_calls=30,
    )
    reviews = _full_reviews()
    (tmp_path / "baseline-001.review.jsonl").write_text(
        "\n".join(review.model_dump_json() for review in reviews) + "\n",
        encoding="utf-8",
    )
    observations = prepare_reviewed_observations(dataset, first, reviews)
    write_reviewed_observations(
        tmp_path / "baseline-001.observations.jsonl", observations
    )
    report = evaluate_dataset(
        dataset,
        observations,
        run=EvaluationRunDescriptor(
            run_id="baseline-001",
            execution_mode="live",
            provider=first.run.provider,
            model=first.run.model,
            prompt_version=first.run.prompt_version,
            judge_version=APPROVED_JUDGE_VERSION,
        ),
    )
    write_evaluation_report(tmp_path / "baseline-001.report.json", report)

    original_campaign = budget.read_bytes()
    campaign_payload = json.loads(original_campaign)
    campaign_payload["reservations"].append(
        {"run_id": "baseline-001", "case_id": "unknown-case"}
    )
    budget.write_text(json.dumps(campaign_payload), encoding="utf-8")
    extra_provider = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="prior-run evidence"):
        _collect_live_baseline(
            dataset,
            output_path=tmp_path / "baseline-002.candidates.json",
            budget_path=budget,
            run=_v3_run(run_id="baseline-002"),
            provider=extra_provider,
            max_new_calls=1,
        )
    assert extra_provider.requests == []

    budget.write_bytes(original_campaign)
    campaign_payload = json.loads(original_campaign)
    campaign_payload["reservations"][0:2] = reversed(
        campaign_payload["reservations"][0:2]
    )
    budget.write_text(json.dumps(campaign_payload), encoding="utf-8")
    reordered_provider = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="prior-run evidence"):
        _collect_live_baseline(
            dataset,
            output_path=tmp_path / "baseline-002.candidates.json",
            budget_path=budget,
            run=_v3_run(run_id="baseline-002"),
            provider=reordered_provider,
            max_new_calls=1,
        )
    assert reordered_provider.requests == []
    budget.write_bytes(original_campaign)

    authorized_provider = FakeProvider(provider_variant="DeepInfra")
    second = _collect_live_baseline(
        dataset,
        output_path=tmp_path / "baseline-002.candidates.json",
        budget_path=budget,
        run=_v3_run(run_id="baseline-002"),
        provider=authorized_provider,
        max_new_calls=1,
    )
    assert len(second.attempts) == 1
    assert len(authorized_provider.requests) == 1


def test_v2_collection_is_hard_stopped_at_ten_calls_without_canary_report(
    tmp_path: Path,
) -> None:
    output = tmp_path / "baseline-001.candidates.json"
    budget = tmp_path / "campaign.json"
    provider = FakeProvider(provider_variant="DeepInfra")

    with pytest.raises(BaselineValidationError, match="passing canary"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_v2_run(),
            provider=provider,
            max_new_calls=11,
        )

    assert provider.requests == []

    state = _collect_live_baseline(
        _dataset(),
        output_path=output,
        budget_path=budget,
        run=_v2_run(),
        provider=provider,
        max_new_calls=10,
    )
    assert len(provider.requests) == 10
    assert [
        json.loads(request.messages[-1]["content"])["task"]
        for request in provider.requests
    ] == [
        next(case.input for case in _dataset().cases if case.case_id == case_id)
        for case_id in V2_CANARY_CASE_IDS
    ]
    assert all(request.response_format == "json_object" for request in provider.requests)
    assert len(state.attempts) == 10

    resume_provider = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="passing canary"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_v2_run(),
            provider=resume_provider,
            max_new_calls=1,
        )
    assert resume_provider.requests == []


def test_v2_rejects_unattested_provider_policy_before_writing_or_calling(
    tmp_path: Path,
) -> None:
    provider = FakeProvider(execution_binding=None, provider_variant="DeepInfra")

    with pytest.raises(BaselineValidationError, match="execution policy"):
        _collect_live_baseline(
            _dataset(),
            output_path=tmp_path / "baseline-001.candidates.json",
            budget_path=tmp_path / "campaign.json",
            run=_v2_run(),
            provider=provider,
            max_new_calls=1,
        )

    assert provider.requests == []
    assert list(tmp_path.iterdir()) == []


def test_passing_canary_authorizes_first_run_resume_and_later_runs(
    tmp_path: Path,
) -> None:
    dataset = _dataset()
    first_output = tmp_path / "baseline-001.candidates.json"
    budget = tmp_path / "campaign.json"
    first = _collect_live_baseline(
        dataset,
        output_path=first_output,
        budget_path=budget,
        run=_v2_run(),
        provider=FakeProvider(provider_variant="DeepInfra"),
        max_new_calls=10,
    )
    cases_by_id = {case.case_id: case for case in dataset.cases}
    reviews = [
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
    report_path = tmp_path / "baseline-001.canary.report.json"
    report = evaluate_canary(dataset, first, reviews)
    write_canary_report(report_path, report)
    (tmp_path / "baseline-001.canary.review.jsonl").write_text(
        "\n".join(review.model_dump_json() for review in reviews) + "\n",
        encoding="utf-8",
    )
    campaign_path = tmp_path / "campaign.json"
    original_campaign = campaign_path.read_bytes()
    campaign_payload = json.loads(original_campaign)
    campaign_payload["reservations"] = []
    campaign_path.write_text(json.dumps(campaign_payload), encoding="utf-8")
    ledger_bypass_provider = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="ledger"):
        _collect_live_baseline(
            dataset,
            output_path=tmp_path / "baseline-002.candidates.json",
            budget_path=budget,
            run=_v2_run(run_id="baseline-002"),
            provider=ledger_bypass_provider,
            max_new_calls=1,
        )
    assert ledger_bypass_provider.requests == []
    campaign_path.write_bytes(original_campaign)

    first_resume_provider = FakeProvider(provider_variant="DeepInfra")
    resumed = _collect_live_baseline(
        dataset,
        output_path=first_output,
        budget_path=budget,
        run=_v2_run(),
        provider=first_resume_provider,
        max_new_calls=1,
    )
    assert len(first_resume_provider.requests) == 1
    assert len(resumed.attempts) == 11

    second_provider = FakeProvider(provider_variant="DeepInfra")
    second = _collect_live_baseline(
        dataset,
        output_path=tmp_path / "baseline-002.candidates.json",
        budget_path=budget,
        run=_v2_run(run_id="baseline-002"),
        provider=second_provider,
        max_new_calls=1,
    )
    assert len(second_provider.requests) == 1
    assert len(second.attempts) == 1

    tampered_reviews = list(reviews)
    injection_index = next(
        index
        for index, review in enumerate(tampered_reviews)
        if review.explicit_refusal is not None
    )
    tampered_reviews[injection_index] = tampered_reviews[injection_index].model_copy(
        update={"explicit_refusal": False}
    )
    (tmp_path / "baseline-001.canary.review.jsonl").write_text(
        "\n".join(review.model_dump_json() for review in tampered_reviews) + "\n",
        encoding="utf-8",
    )
    blocked_provider = FakeProvider(provider_variant="DeepInfra")
    with pytest.raises(BaselineValidationError, match="missing or invalid"):
        _collect_live_baseline(
            dataset,
            output_path=tmp_path / "baseline-003.candidates.json",
            budget_path=budget,
            run=_v2_run(run_id="baseline-003"),
            provider=blocked_provider,
            max_new_calls=1,
        )
    assert blocked_provider.requests == []


@pytest.mark.parametrize(
    ("provider", "expected_code"),
    [
        (FakeProvider(provider_variant="other"), "AI_PROVIDER_METADATA_MISMATCH"),
        (
            FakeProvider(provider_variant="DeepInfra", finish_reason="length"),
            "AI_PROVIDER_RESPONSE_INCOMPLETE",
        ),
    ],
)
def test_v2_rejects_wrong_upstream_or_incomplete_response(
    tmp_path: Path, provider: FakeProvider, expected_code: str
) -> None:
    output = tmp_path / "baseline-001.candidates.json"

    expected_error = (
        BaselineProviderFailure
        if expected_code == "AI_PROVIDER_METADATA_MISMATCH"
        else BaselineResponseFailure
    )
    with pytest.raises(expected_error):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=tmp_path / "campaign.json",
            run=_v2_run(),
            provider=provider,
            max_new_calls=1,
        )

    attempt = load_baseline_run(output).attempts[0]
    assert attempt.error_code == expected_code


def test_candidate_response_requires_the_exact_strict_envelope() -> None:
    valid = json.dumps({"answer": "Đúng.", "cited_source_ids": ["source-001"]})
    answer, citations, format_valid = parse_candidate_response(valid)
    assert (answer, citations, format_valid) == ("Đúng.", ["source-001"], True)

    raw = "```json\n" + valid + "\n```"
    assert parse_candidate_response(raw) == (raw, [], False)
    duplicate = json.dumps(
        {"answer": "Đúng.", "cited_source_ids": ["source-001", "source-001"]}
    )
    assert parse_candidate_response(duplicate) == (duplicate, [], False)


def test_collection_caps_calls_and_resume_never_repeats_a_case(tmp_path: Path) -> None:
    output = tmp_path / "baseline.json"
    budget = tmp_path / "campaign.json"
    first_provider = FakeProvider()

    first = _collect_live_baseline(
        _dataset(),
        output_path=output,
        budget_path=budget,
        run=_run(),
        provider=first_provider,
        max_new_calls=1,
    )

    assert len(first_provider.requests) == 1
    assert [attempt.case_id for attempt in first.attempts] == ["brief-001"]
    assert first.attempts[0].status == "succeeded"
    assert first.attempts[0].estimated_cost_usd is None
    assert first_provider.requests[0].temperature == 0.0
    assert first_provider.requests[0].max_tokens == 1000

    second_provider = FakeProvider()
    second = _collect_live_baseline(
        _dataset(),
        output_path=output,
        budget_path=budget,
        run=_run(),
        provider=second_provider,
        max_new_calls=2,
    )

    assert len(second_provider.requests) == 2
    called_ids = [
        json.loads(request.messages[-1]["content"])["task"]
        for request in second_provider.requests
    ]
    brief_one = next(case for case in _dataset().cases if case.case_id == "brief-001")
    assert brief_one.input not in called_ids
    assert len(second.attempts) == 3
    assert len(load_baseline_run(output).attempts) == 3


def test_collection_refuses_metadata_changes_before_calling_provider(
    tmp_path: Path,
) -> None:
    output = tmp_path / "baseline.json"
    budget = tmp_path / "campaign.json"
    _collect_live_baseline(
        _dataset(),
        output_path=output,
        budget_path=budget,
        run=_run(),
        provider=FakeProvider(),
        max_new_calls=1,
    )
    provider = FakeProvider()

    with pytest.raises(BaselineValidationError, match="approved campaign"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_run(model="other/model"),
            provider=provider,
            max_new_calls=1,
        )

    assert provider.requests == []


def test_provider_failure_is_sanitized_persisted_and_not_retried(
    tmp_path: Path,
) -> None:
    output = tmp_path / "baseline.json"
    budget = tmp_path / "campaign.json"
    secret = "provider-secret-detail"
    provider = FakeProvider(error=AIProviderError(secret))

    with pytest.raises(BaselineProviderFailure, match="provider call failed") as error:
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_run(),
            provider=provider,
            max_new_calls=1,
        )

    assert secret not in str(error.value)
    saved = load_baseline_run(output)
    assert saved.attempts[0].status == "provider_failed"
    assert saved.attempts[0].error_code == "AI_PROVIDER_FAILURE"

    second_provider = FakeProvider()
    with pytest.raises(BaselineValidationError, match="automatic retry is disabled"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_run(),
            provider=second_provider,
            max_new_calls=1,
        )
    assert second_provider.requests == []


@pytest.mark.parametrize("raw_text", ["", "not-json"])
def test_invalid_provider_response_is_terminal_and_not_counted_complete(
    tmp_path: Path, raw_text: str
) -> None:
    output = tmp_path / "baseline.json"
    budget = tmp_path / "campaign.json"

    with pytest.raises(BaselineResponseFailure, match="strict envelope"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_run(),
            provider=FakeProvider(raw_text=raw_text),
            max_new_calls=1,
        )

    saved = load_baseline_run(output)
    assert saved.attempts[0].status == "invalid_response"
    assert saved.attempts[0].response_format_valid is False
    assert saved.attempts[0].error_code == "AI_PROVIDER_RESPONSE_INVALID"

    provider = FakeProvider()
    resumed = _collect_live_baseline(
        _dataset(),
        output_path=output,
        budget_path=budget,
        run=_run(),
        provider=provider,
        max_new_calls=1,
    )
    assert len(provider.requests) == 1
    assert len(resumed.attempts) == 2
    assert resumed.attempts[0].status == "invalid_response"
    assert resumed.attempts[1].status == "succeeded"


def test_campaign_rejects_a_different_self_consistent_approved_dataset(
    tmp_path: Path,
) -> None:
    dataset = _dataset()
    changed_case = dataset.cases[0].model_copy(update={"input": "Changed task"})
    changed_cases = [changed_case, *dataset.cases[1:]]
    fingerprint = golden_dataset_fingerprint(changed_cases)
    changed = dataset.model_copy(
        update={
            "cases": changed_cases,
            "fingerprint_sha256": fingerprint,
            "approval": dataset.approval.model_copy(
                update={"dataset_sha256": fingerprint}
            ),
        }
    )
    provider = FakeProvider()

    with pytest.raises(BaselineValidationError, match="dataset fingerprint mismatch"):
        _collect_live_baseline(
            changed,
            output_path=tmp_path / "baseline.json",
            budget_path=tmp_path / "campaign.json",
            run=_run().model_copy(update={"dataset_sha256": fingerprint}),
            provider=provider,
            max_new_calls=1,
        )

    assert provider.requests == []


def test_interrupted_attempt_and_concurrent_lock_fail_without_a_call(
    tmp_path: Path,
) -> None:
    output = tmp_path / "baseline.json"
    budget = tmp_path / "campaign.json"
    lock = tmp_path / ".baseline.json.lock"
    lock.write_text("", encoding="utf-8")
    provider = FakeProvider()
    with pytest.raises(BaselineValidationError, match="already being collected"):
        _collect_live_baseline(
            _dataset(),
            output_path=output,
            budget_path=budget,
            run=_run(),
            provider=provider,
            max_new_calls=1,
        )
    assert provider.requests == []


def test_completed_baseline_is_an_idempotent_no_call(tmp_path: Path) -> None:
    output = tmp_path / "baseline.json"
    budget = tmp_path / "campaign.json"
    _collect_live_baseline(
        _dataset(),
        output_path=output,
        budget_path=budget,
        run=_run(),
        provider=FakeProvider(),
        max_new_calls=40,
    )
    provider = FakeProvider()

    completed = _collect_live_baseline(
        _dataset(),
        output_path=output,
        budget_path=budget,
        run=_run(),
        provider=provider,
        max_new_calls=1,
    )

    assert provider.requests == []
    assert len(completed.attempts) == 40


def test_campaign_allows_only_the_three_approved_runs(tmp_path: Path) -> None:
    budget = tmp_path / "campaign.json"
    run = _run()
    reservations = [
        {"run_id": f"baseline-{run_index:03d}", "case_id": case.case_id}
        for run_index in range(1, 4)
        for case in _dataset().cases
    ]
    campaign = BaselineCampaignFile.model_validate(
        {
            "schema_version": BASELINE_SCHEMA_VERSION,
            "campaign_id": run.campaign_id,
            "dataset_sha256": run.dataset_sha256,
            "provider": run.provider,
            "model": run.model,
            "prompt_version": run.prompt_version,
            "prompt_template_sha256": run.prompt_template_sha256,
            "temperature": run.temperature,
            "max_output_tokens": run.max_output_tokens,
            "approved_run_ids": list(APPROVED_RUN_IDS),
            "max_total_calls": 120,
            "reservations": reservations,
        }
    )
    budget.write_text(
        json.dumps(campaign.model_dump(mode="json")),
        encoding="utf-8",
    )
    provider = FakeProvider()

    with pytest.raises(BaselineValidationError, match="approved campaign"):
        _collect_live_baseline(
            _dataset(),
            output_path=tmp_path / "baseline-004.json",
            budget_path=budget,
            run=_run(run_id="baseline-004"),
            provider=provider,
            max_new_calls=1,
        )

    assert provider.requests == []


def test_cli_uses_canonical_paths_and_disables_sdk_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    provider = FakeProvider()
    received_retry_values = []
    monkeypatch.setattr(live_baseline, "APPROVED_CAMPAIGN_ROOT", tmp_path)
    monkeypatch.setattr(
        live_baseline, "APPROVED_BUDGET_PATH", tmp_path / "campaign.json"
    )

    def build_provider(*, max_retries: int, routing_policy):
        assert routing_policy is None
        received_retry_values.append(max_retries)
        return provider

    monkeypatch.setattr(live_baseline_cli, "OpenRouterAdapter", build_provider)

    exit_code = live_baseline_cli.main(
        [
            str(DATASET_PATH),
            "--approval-manifest",
            str(APPROVAL_PATH),
            "--run-id",
            "baseline-001",
            "--max-new-calls",
            "1",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert received_retry_values == [0]
    assert len(provider.requests) == 1
    assert (tmp_path / "campaign.json").exists()
    assert (tmp_path / "baseline-001.candidates.json").exists()
    assert "AI_BASELINE_PARTIAL" in output
    assert "Câu trả lời kiểm soát" not in output


def test_v2_cli_pins_routing_json_mode_and_ten_call_canary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    provider = FakeProvider(provider_variant="DeepInfra")
    received = []
    monkeypatch.setattr(live_baseline, "V2_APPROVED_CAMPAIGN_ROOT", tmp_path)

    def build_provider(*, max_retries: int, routing_policy):
        received.append((max_retries, routing_policy))
        return provider

    monkeypatch.setattr(live_baseline_cli, "OpenRouterAdapter", build_provider)

    exit_code = live_baseline_cli.main(
        [
            str(DATASET_PATH),
            "--approval-manifest",
            str(APPROVAL_PATH),
            "--campaign",
            V2_APPROVED_CAMPAIGN_ID,
            "--run-id",
            "baseline-001",
            "--max-new-calls",
            "10",
        ]
    )

    assert exit_code == 0
    assert len(received) == 1
    retries, routing = received[0]
    assert retries == 0
    assert routing.request_body() == {
        "only": ["deepinfra"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
    }
    assert len(provider.requests) == 10
    assert all(request.response_format == "json_object" for request in provider.requests)
    assert (tmp_path / "baseline-001.candidates.json").exists()
    assert "AI_BASELINE_PARTIAL" in capsys.readouterr().out


def test_v3_cli_uses_fixed_campaign_model_without_changing_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    provider = FakeProvider(provider_variant="DeepInfra")
    received = []
    monkeypatch.setattr(live_baseline, "V3_APPROVED_CAMPAIGN_ROOT", tmp_path)

    def build_provider(*, max_retries: int, routing_policy):
        received.append((max_retries, routing_policy))
        return provider

    monkeypatch.setattr(live_baseline_cli, "OpenRouterAdapter", build_provider)

    exit_code = live_baseline_cli.main(
        [
            str(DATASET_PATH),
            "--approval-manifest",
            str(APPROVAL_PATH),
            "--campaign",
            V3_APPROVED_CAMPAIGN_ID,
            "--run-id",
            "baseline-001",
            "--max-new-calls",
            "10",
        ]
    )

    assert exit_code == 0
    assert len(received) == 1
    assert len(provider.requests) == 10
    assert {request.model for request in provider.requests} == {V3_APPROVED_MODEL}
    assert all(request.response_format == "json_object" for request in provider.requests)
    assert "AI_BASELINE_PARTIAL" in capsys.readouterr().out


@pytest.mark.parametrize("credential", ["", "   "])
def test_cli_rejects_missing_credential_before_reserving_or_calling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, credential: str
) -> None:
    provider_constructed = False
    monkeypatch.setattr(live_baseline, "APPROVED_CAMPAIGN_ROOT", tmp_path)
    monkeypatch.setattr(
        live_baseline, "APPROVED_BUDGET_PATH", tmp_path / "campaign.json"
    )
    monkeypatch.setattr(
        live_baseline_cli.settings, "OPENROUTER_API_KEY", credential
    )

    def build_provider(*, max_retries: int, routing_policy):
        nonlocal provider_constructed
        del max_retries, routing_policy
        provider_constructed = True
        return FakeProvider()

    monkeypatch.setattr(live_baseline_cli, "OpenRouterAdapter", build_provider)

    exit_code = live_baseline_cli.main(
        [
            str(DATASET_PATH),
            "--approval-manifest",
            str(APPROVAL_PATH),
            "--run-id",
            "baseline-001",
            "--max-new-calls",
            "1",
        ]
    )

    assert exit_code == 1
    assert "requires a configured provider credential" in capsys.readouterr().out
    assert provider_constructed is False
    assert list(tmp_path.iterdir()) == []
