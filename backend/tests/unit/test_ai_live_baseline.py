from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import app.ai.evaluation.live_baseline as live_baseline
import scripts.run_ai_live_baseline as live_baseline_cli
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
    BaselineProviderFailure,
    BaselineAttempt,
    BaselineCampaignFile,
    BaselineRunDescriptor,
    BaselineResponseFailure,
    BaselineValidationError,
    _collect_live_baseline,
    build_candidate_messages,
    load_baseline_run,
    parse_candidate_response,
)
from app.ai.provider import (
    AIProviderError,
    GenerateRequest,
    GenerateResult,
    TokenUsage,
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
    requests: list[GenerateRequest] = field(default_factory=list)

    def generate(self, request: GenerateRequest) -> GenerateResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        source_id = json.loads(request.messages[-1]["content"])["sources"][0][
            "source_id"
        ]
        text = self.raw_text
        if text is None:
            text = json.dumps(
                {
                    "answer": "Câu trả lời kiểm soát.",
                    "cited_source_ids": [source_id],
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
            finish_reason="stop",
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

    def build_provider(*, max_retries: int):
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

    def build_provider(*, max_retries: int):
        nonlocal provider_constructed
        del max_retries
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
