from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai.evaluation.live_baseline import V8_ROUTING_POLICY_SHA256
from app.ai.evaluation.regression_collection import (
    AIRegressionCollectionError,
    attest_ai008_regression,
    collect_ai008_regression,
)
from app.ai.provider import (
    GenerateRequest,
    GenerateResult,
    ProviderExecutionBinding,
    TokenUsage,
)
from tests.unit.test_ai_baseline_review import _dataset
from tests.unit.test_ai_baseline_comparison import _v8_reviews


class _RegressionProvider:
    def __init__(
        self,
        *,
        binding: ProviderExecutionBinding | None = None,
        invalid_at: int | None = None,
    ) -> None:
        self.execution_binding = binding or ProviderExecutionBinding(
            max_retries=0,
            routing_policy_sha256=V8_ROUTING_POLICY_SHA256,
        )
        self.invalid_at = invalid_at
        self.requests: list[GenerateRequest] = []

    def generate(self, request: GenerateRequest) -> GenerateResult:
        self.requests.append(request)
        call_number = len(self.requests)
        source_ids = [
            source["source_id"] for source in json.loads(request.messages[1]["content"])["sources"]
        ]
        text = (
            "not-json"
            if self.invalid_at == call_number
            else json.dumps(
                {
                    "answer": "Nội dung học tập an toàn.",
                    "cited_source_ids": source_ids,
                },
                ensure_ascii=False,
            )
        )
        return GenerateResult(
            text=text,
            tool_calls=None,
            provider="openrouter",
            model="openai/gpt-4.1-mini",
            usage=TokenUsage(input_tokens=390, output_tokens=70),
            latency_ms=100,
            finish_reason="stop",
            provider_variant="OpenAI",
        )


@pytest.mark.parametrize(("scope", "expected_calls"), [("pr", 20), ("full", 40)])
def test_collection_enforces_exact_scope_and_sanitized_manifest(
    tmp_path: Path, scope: str, expected_calls: int
) -> None:
    provider = _RegressionProvider()
    candidate_path = tmp_path / "candidates.json"
    manifest_path = tmp_path / "manifest.json"

    manifest = collect_ai008_regression(
        _dataset(),
        scope=scope,  # type: ignore[arg-type]
        commit_sha="a" * 40,
        provider=provider,
        candidate_path=candidate_path,
        manifest_path=manifest_path,
    )

    assert manifest.structural_gate_passed is True
    assert manifest.case_count == expected_calls
    assert manifest.valid_response_envelopes == expected_calls
    assert manifest.semantic_status == "pending_independent_review"
    assert manifest.cost_gate_active is False
    assert len(provider.requests) == expected_calls
    assert all(request.model == "openai/gpt-4.1-mini" for request in provider.requests)
    assert all(request.temperature == 0 for request in provider.requests)
    assert all(request.max_tokens == 1000 for request in provider.requests)
    assert all(request.response_format == "json_object" for request in provider.requests)
    assert "Nội dung học tập" not in manifest_path.read_text(encoding="utf-8")
    assert "Nội dung học tập" in candidate_path.read_text(encoding="utf-8")


def test_provider_policy_mismatch_fails_before_a_call(tmp_path: Path) -> None:
    provider = _RegressionProvider(
        binding=ProviderExecutionBinding(
            max_retries=1,
            routing_policy_sha256=V8_ROUTING_POLICY_SHA256,
        )
    )

    with pytest.raises(AIRegressionCollectionError, match="provider policy"):
        collect_ai008_regression(
            _dataset(),
            scope="pr",
            commit_sha="b" * 40,
            provider=provider,
            candidate_path=tmp_path / "candidates.json",
            manifest_path=tmp_path / "manifest.json",
        )

    assert provider.requests == []


def test_invalid_envelope_stops_without_retry_and_preserves_checkpoint(
    tmp_path: Path,
) -> None:
    provider = _RegressionProvider(invalid_at=3)
    candidate_path = tmp_path / "candidates.json"

    with pytest.raises(AIRegressionCollectionError, match="envelope"):
        collect_ai008_regression(
            _dataset(),
            scope="pr",
            commit_sha="c" * 40,
            provider=provider,
            candidate_path=candidate_path,
            manifest_path=tmp_path / "manifest.json",
        )

    checkpoint = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert len(provider.requests) == 3
    assert len(checkpoint["candidates"]) == 2


def test_independent_review_attestation_binds_candidate_and_passes(
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidates.json"
    collection_manifest_path = tmp_path / "manifest.json"
    collect_ai008_regression(
        _dataset(),
        scope="pr",
        commit_sha="d" * 40,
        provider=_RegressionProvider(),
        candidate_path=candidate_path,
        manifest_path=collection_manifest_path,
    )
    selected_ids = {
        item["case_id"]
        for item in json.loads(candidate_path.read_text(encoding="utf-8"))["candidates"]
    }
    review_path = tmp_path / "reviews.jsonl"
    review_path.write_text(
        "".join(
            json.dumps(review.model_dump(mode="json"), sort_keys=True) + "\n"
            for review in _v8_reviews()
            if review.case_id in selected_ids
        ),
        encoding="utf-8",
    )

    attestation = attest_ai008_regression(
        _dataset(),
        candidate_path=candidate_path,
        collection_manifest_path=collection_manifest_path,
        review_path=review_path,
        collection_run_id="12345",
        candidate_artifact_digest=f"sha256:{'1' * 64}",
        collection_manifest_artifact_digest=f"sha256:{'2' * 64}",
        reviewer_actor="independent-reviewer",
        review_ref="e" * 40,
        expected_commit_sha="d" * 40,
        attestation_path=tmp_path / "attestation.json",
    )

    assert attestation.passed is True
    assert attestation.failure_codes == []
    assert attestation.safe_continuations == attestation.safe_continuation_cases == 8
    assert attestation.explicit_refusals == attestation.explicit_refusal_cases == 1

    tampered_manifest = tmp_path / "tampered-manifest.json"
    manifest_payload = json.loads(collection_manifest_path.read_text(encoding="utf-8"))
    manifest_payload["candidate_sha256"] = "0" * 64
    tampered_manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
    with pytest.raises(AIRegressionCollectionError, match="binding"):
        attest_ai008_regression(
            _dataset(),
            candidate_path=candidate_path,
            collection_manifest_path=tampered_manifest,
            review_path=review_path,
            collection_run_id="12345",
            candidate_artifact_digest=f"sha256:{'1' * 64}",
            collection_manifest_artifact_digest=f"sha256:{'2' * 64}",
            reviewer_actor="independent-reviewer",
            review_ref="e" * 40,
            expected_commit_sha="d" * 40,
            attestation_path=tmp_path / "tampered-attestation.json",
        )


def test_attestation_rejects_wrong_source_commit_before_scoring(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidates.json"
    collection_manifest_path = tmp_path / "manifest.json"
    collect_ai008_regression(
        _dataset(),
        scope="pr",
        commit_sha="f" * 40,
        provider=_RegressionProvider(),
        candidate_path=candidate_path,
        manifest_path=collection_manifest_path,
    )
    review_path = tmp_path / "reviews.jsonl"
    review_path.write_text(
        "".join(
            json.dumps(review.model_dump(mode="json"), sort_keys=True) + "\n"
            for review in _v8_reviews()
            if review.case_id
            in {
                item["case_id"]
                for item in json.loads(candidate_path.read_text(encoding="utf-8"))["candidates"]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AIRegressionCollectionError, match="binding"):
        attest_ai008_regression(
            _dataset(),
            candidate_path=candidate_path,
            collection_manifest_path=collection_manifest_path,
            review_path=review_path,
            collection_run_id="12346",
            candidate_artifact_digest=f"sha256:{'1' * 64}",
            collection_manifest_artifact_digest=f"sha256:{'2' * 64}",
            reviewer_actor="independent-reviewer",
            review_ref="e" * 40,
            expected_commit_sha="0" * 40,
            attestation_path=tmp_path / "attestation.json",
        )


def test_workflow_protects_provider_secret_and_separates_semantic_review() -> None:
    workflow = (
        Path(__file__).resolve().parents[3] / ".github/workflows/ai-regression.yml"
    ).read_text(encoding="utf-8")

    assert "cron:" in workflow
    assert "ai-regression-approved" in workflow
    assert "head.repo.full_name == github.repository" in workflow
    assert "environment: ai-regression" in workflow
    assert "OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}" in workflow
    assert "--scope $REGRESSION_SCOPE" in workflow
    assert "retention-days: 3" in workflow
    assert "pending_independent_review" not in workflow
    assert "ai-baseline-integrity" in workflow
    attestation_workflow = (
        Path(__file__).resolve().parents[3] / ".github/workflows/ai-regression-attestation.yml"
    ).read_text(encoding="utf-8")
    assert "environment: ai-regression-review" in attestation_workflow
    assert "checks: write" in attestation_workflow
    assert "AI semantic regression" in attestation_workflow
    assert "OPENROUTER_API_KEY" not in attestation_workflow
    assert ".github/workflows/ai-regression.yml" in attestation_workflow
    assert ".conclusion" in attestation_workflow
    assert ".repository.full_name" in attestation_workflow
    assert "candidate_digest" in attestation_workflow
    assert "manifest_digest" in attestation_workflow
    assert "source_commit_sha" not in attestation_workflow
    assert '--review-ref "${{ inputs.' not in attestation_workflow
