from __future__ import annotations

import base64
import copy
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.ai.evaluation.dataset import (
    EXPECTED_COMPLETE_DISTRIBUTION,
    GoldenDatasetCase,
    GoldenDatasetValidationError,
    TRUST_ROOT_SHA256_ENV,
    TrustedApproverStore,
    approval_signing_payload,
    load_golden_dataset,
    trusted_approver_store_fingerprint,
)
from scripts.validate_ai_golden_dataset import main


def _case(case_id: str = "rag.case-001", use_case: str = "rag_chat") -> dict:
    return {
        "schema_version": "1.0",
        "case_id": case_id,
        "use_case": use_case,
        "language": "vi",
        "input": "Summarize the approved source.",
        "reference_context": [
            {"source_id": "source.one", "content": "Approved safe source text."}
        ],
        "expected_answer": "A grounded answer using the approved source.",
        "rubric": [],
        "required_source_ids": ["source.one"],
        "injection_label": "none",
        "sensitivity": "internal",
        "approval": {
            "approval_source": "admin",
            "approved_by": "test-admin-001",
            "approved_at": "2026-08-25T10:00:00+07:00",
            "approval_version": "approval-v1",
            "key_id": "test-admin-key",
            "signature_base64": base64.b64encode(bytes(64)).decode(),
        },
    }


def _trust_material() -> tuple[Ed25519PrivateKey, TrustedApproverStore, dict, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    raw_store = {
        "schema_version": "1.0",
        "approvers": [
            {
                "key_id": "test-admin-key",
                "approval_source": "admin",
                "approved_by": "test-admin-001",
                "public_key_base64": base64.b64encode(public_key).decode(),
            }
        ],
    }
    store = TrustedApproverStore.model_validate(raw_store)
    return private_key, store, raw_store, trusted_approver_store_fingerprint(store)


def _sign_case(case: dict, private_key: Ed25519PrivateKey) -> dict:
    signed = copy.deepcopy(case)
    parsed = GoldenDatasetCase.model_validate(signed)
    signed["approval"]["signature_base64"] = base64.b64encode(
        private_key.sign(approval_signing_payload(parsed))
    ).decode()
    return signed


def _write_jsonl(path: Path, cases: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )


def _complete_cases(private_key: Ed25519PrivateKey) -> list[dict]:
    cases: list[dict] = []
    for use_case, count in EXPECTED_COMPLETE_DISTRIBUTION.items():
        for index in range(1, count + 1):
            raw_case = _case(f"{use_case}.case-{index:03d}", use_case)
            cases.append(_sign_case(raw_case, private_key))
    return cases


@pytest.mark.unit
def test_partial_dataset_validates_signatures_and_deterministic_fingerprint(
    tmp_path: Path,
) -> None:
    private_key, trust_store, _, trust_root = _trust_material()
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    cases = [
        _sign_case(_case("rag.case-002"), private_key),
        _sign_case(_case("rag.case-001"), private_key),
    ]
    _write_jsonl(first_path, cases)
    _write_jsonl(second_path, list(reversed(cases)))

    first = load_golden_dataset(
        first_path,
        require_complete=False,
        trust_store=trust_store,
        trusted_root_sha256=trust_root,
    )
    second = load_golden_dataset(
        second_path,
        require_complete=False,
        trust_store=trust_store,
        trusted_root_sha256=trust_root,
    )

    assert len(first.cases) == 2
    assert first.approvals_verified is True
    assert first.fingerprint_sha256 == second.fingerprint_sha256


@pytest.mark.unit
def test_complete_dataset_enforces_approved_distribution(tmp_path: Path) -> None:
    private_key, trust_store, _, trust_root = _trust_material()
    dataset_path = tmp_path / "complete.jsonl"
    _write_jsonl(dataset_path, _complete_cases(private_key))

    dataset = load_golden_dataset(
        dataset_path,
        trust_store=trust_store,
        trusted_root_sha256=trust_root,
    )

    assert len(dataset.cases) == 40
    assert dataset.distribution == EXPECTED_COMPLETE_DISTRIBUTION


@pytest.mark.unit
def test_incomplete_dataset_is_not_accepted_as_complete(tmp_path: Path) -> None:
    private_key, trust_store, _, trust_root = _trust_material()
    dataset_path = tmp_path / "partial.jsonl"
    _write_jsonl(dataset_path, [_sign_case(_case(), private_key)])

    with pytest.raises(GoldenDatasetValidationError, match="complete dataset requires"):
        load_golden_dataset(
            dataset_path,
            trust_store=trust_store,
            trusted_root_sha256=trust_root,
        )


@pytest.mark.unit
def test_trusted_approval_is_required_by_default(tmp_path: Path) -> None:
    dataset_path = tmp_path / "unsigned-trust.jsonl"
    _write_jsonl(dataset_path, [_case()])

    with pytest.raises(GoldenDatasetValidationError, match="trusted approval"):
        load_golden_dataset(dataset_path, require_complete=False)


@pytest.mark.unit
def test_forged_signature_is_rejected(tmp_path: Path) -> None:
    _, trust_store, _, trust_root = _trust_material()
    attacker_key = Ed25519PrivateKey.generate()
    dataset_path = tmp_path / "forged.jsonl"
    _write_jsonl(dataset_path, [_sign_case(_case(), attacker_key)])

    with pytest.raises(GoldenDatasetValidationError, match="signature is invalid"):
        load_golden_dataset(
            dataset_path,
            require_complete=False,
            trust_store=trust_store,
            trusted_root_sha256=trust_root,
        )


@pytest.mark.unit
def test_untrusted_approval_identity_is_rejected(tmp_path: Path) -> None:
    private_key, trust_store, _, trust_root = _trust_material()
    dataset_path = tmp_path / "wrong-identity.jsonl"
    case = _sign_case(_case(), private_key)
    case["approval"]["approved_by"] = "owner-reviewer-001"
    _write_jsonl(dataset_path, [case])

    with pytest.raises(GoldenDatasetValidationError, match="identity does not match"):
        load_golden_dataset(
            dataset_path,
            require_complete=False,
            trust_store=trust_store,
            trusted_root_sha256=trust_root,
        )


@pytest.mark.unit
def test_duplicate_case_id_is_rejected(tmp_path: Path) -> None:
    dataset_path = tmp_path / "duplicate.jsonl"
    _write_jsonl(dataset_path, [_case(), _case()])

    with pytest.raises(GoldenDatasetValidationError, match="duplicate case IDs"):
        load_golden_dataset(
            dataset_path,
            require_complete=False,
            require_trusted_approval=False,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("transform", "expected_error"),
    [
        (lambda case: case.pop("approval"), "missing"),
        (lambda case: case.update(schema_version="2.0"), "literal_error"),
        (lambda case: case.update(unexpected=True), "extra_forbidden"),
        (
            lambda case: case["required_source_ids"].append("source.missing"),
            "value_error",
        ),
        (lambda case: case["approval"].update(signature_base64="invalid"), "string_too_short"),
    ],
)
def test_invalid_case_contract_is_rejected_without_echoing_payload(
    tmp_path: Path,
    transform,
    expected_error: str,
) -> None:
    dataset_path = tmp_path / "invalid.jsonl"
    case = copy.deepcopy(_case())
    transform(case)
    _write_jsonl(dataset_path, [case])

    with pytest.raises(GoldenDatasetValidationError, match=expected_error):
        load_golden_dataset(
            dataset_path,
            require_complete=False,
            require_trusted_approval=False,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "secret_value",
    [
        "api_key=" + "sk-" + "live-abcdefghijklmnop",
        "gh" + "p_abcdefghijklmnopqrstuvwxyz1234567890",
        "github_" + "pat_abcdefghijklmnopqrstuvwxyz1234567890",
        "AI" + "za1234567890abcdefghijklmnopqrstuvwxy",
        "xo" + "xb-1234567890-abcdefghijklmnopqrstuvwxyz",
        "ey" + "Jabcdefghijk.eyJabcdefghijk.abcdefghijkl",
        "postgresql://owner:" + "real-password@localhost/database",
    ],
)
def test_common_secret_formats_are_rejected_without_echoing_value(
    tmp_path: Path,
    secret_value: str,
) -> None:
    dataset_path = tmp_path / "secret.jsonl"
    case = _case()
    case["input"] = secret_value
    _write_jsonl(dataset_path, [case])

    with pytest.raises(GoldenDatasetValidationError, match="value_error") as exc_info:
        load_golden_dataset(
            dataset_path,
            require_complete=False,
            require_trusted_approval=False,
        )

    assert secret_value not in str(exc_info.value)


@pytest.mark.unit
def test_secret_scanning_covers_identifier_fields(tmp_path: Path) -> None:
    secret_value = "github_pat_abcdefghijklmnopqrstuvwxyz1234567890"
    dataset_path = tmp_path / "identifier-secret.jsonl"
    case = _case()
    case["case_id"] = secret_value
    _write_jsonl(dataset_path, [case])

    with pytest.raises(GoldenDatasetValidationError, match="value_error") as exc_info:
        load_golden_dataset(
            dataset_path,
            require_complete=False,
            require_trusted_approval=False,
        )

    assert secret_value not in str(exc_info.value)


@pytest.mark.unit
def test_rubric_can_replace_expected_answer(tmp_path: Path) -> None:
    dataset_path = tmp_path / "rubric.jsonl"
    case = _case()
    case["expected_answer"] = None
    case["rubric"] = [
        {"criterion_id": "grounded", "description": "Uses the source.", "weight": 0.6},
        {"criterion_id": "complete", "description": "Answers fully.", "weight": 0.4},
    ]
    _write_jsonl(dataset_path, [case])

    dataset = load_golden_dataset(
        dataset_path,
        require_complete=False,
        require_trusted_approval=False,
    )

    assert len(dataset.cases[0].rubric) == 2
    assert dataset.approvals_verified is False


@pytest.mark.unit
def test_cli_reports_verified_counts_without_case_content(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    private_key, _, raw_store, trust_root = _trust_material()
    dataset_path = tmp_path / "partial.jsonl"
    trust_path = tmp_path / "trusted-approvers.json"
    case = _case()
    case["input"] = "private-evaluation-sentinel"
    _write_jsonl(dataset_path, [_sign_case(case, private_key)])
    trust_path.write_text(json.dumps(raw_store), encoding="utf-8")
    monkeypatch.setenv(TRUST_ROOT_SHA256_ENV, trust_root)

    exit_code = main(
        [str(dataset_path), "--trust-store", str(trust_path), "--allow-partial"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "AI_GOLDEN_DATASET_OK" in output
    assert "approvals_verified=true" in output
    assert f"trust_root_sha256={trust_root}" in output
    assert "cases=1" in output
    assert "private-evaluation-sentinel" not in output


@pytest.mark.unit
def test_cli_rejects_unpinned_caller_supplied_trust_store(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    private_key, _, raw_store, _ = _trust_material()
    dataset_path = tmp_path / "partial.jsonl"
    trust_path = tmp_path / "attacker-trust-store.json"
    _write_jsonl(dataset_path, [_sign_case(_case(), private_key)])
    trust_path.write_text(json.dumps(raw_store), encoding="utf-8")
    monkeypatch.setenv(TRUST_ROOT_SHA256_ENV, "0" * 64)

    exit_code = main(
        [str(dataset_path), "--trust-store", str(trust_path), "--allow-partial"]
    )
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "does not match the owner-pinned root" in output
    assert "attacker-trust-store" not in output


@pytest.mark.unit
def test_cli_requires_external_owner_trust_anchor(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    private_key, _, raw_store, _ = _trust_material()
    dataset_path = tmp_path / "partial.jsonl"
    trust_path = tmp_path / "trusted-approvers.json"
    _write_jsonl(dataset_path, [_sign_case(_case(), private_key)])
    trust_path.write_text(json.dumps(raw_store), encoding="utf-8")
    monkeypatch.delenv(TRUST_ROOT_SHA256_ENV, raising=False)

    exit_code = main(
        [str(dataset_path), "--trust-store", str(trust_path), "--allow-partial"]
    )
    output = capsys.readouterr().out

    assert exit_code == 1
    assert f"{TRUST_ROOT_SHA256_ENV} is required" in output


@pytest.mark.unit
def test_structure_only_cli_never_claims_approval(tmp_path: Path, capsys) -> None:
    dataset_path = tmp_path / "draft.jsonl"
    _write_jsonl(dataset_path, [_case()])

    exit_code = main([str(dataset_path), "--allow-partial", "--structure-only"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "AI_GOLDEN_DATASET_STRUCTURE_OK" in output
    assert "approvals_verified=false" in output


@pytest.mark.unit
def test_invalid_json_reports_line_without_payload(tmp_path: Path) -> None:
    dataset_path = tmp_path / "invalid.jsonl"
    dataset_path.write_text('{"secret":"do-not-echo"\n', encoding="utf-8")

    with pytest.raises(GoldenDatasetValidationError, match="line 1: invalid JSON") as exc_info:
        load_golden_dataset(
            dataset_path,
            require_complete=False,
            require_trusted_approval=False,
        )

    assert "do-not-echo" not in str(exc_info.value)


@pytest.mark.unit
def test_invalid_utf8_cli_error_has_no_traceback_or_path(tmp_path: Path, capsys) -> None:
    dataset_path = tmp_path / "private-path-sentinel.jsonl"
    dataset_path.write_bytes(b"\xff\xfe\xfa")

    exit_code = main([str(dataset_path), "--allow-partial", "--structure-only"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert output == "AI_GOLDEN_DATASET_INVALID error=dataset file is not valid UTF-8\n"
    assert "private-path-sentinel" not in output


@pytest.mark.unit
def test_missing_file_cli_error_does_not_echo_path(tmp_path: Path, capsys) -> None:
    missing_path = tmp_path / "private-missing-sentinel.jsonl"

    exit_code = main([str(missing_path), "--allow-partial", "--structure-only"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert output == "AI_GOLDEN_DATASET_INVALID error=dataset file does not exist\n"
    assert "private-missing-sentinel" not in output
