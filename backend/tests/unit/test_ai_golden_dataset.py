from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.ai.evaluation.dataset import (
    EXPECTED_COMPLETE_DISTRIBUTION,
    GoldenDatasetApprovalManifest,
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from scripts.validate_ai_golden_dataset import main


def _case(case_id: str = "rag-001", use_case: str = "rag_chat") -> dict:
    return {
        "schema_version": "1.0",
        "case_id": case_id,
        "use_case": use_case,
        "language": "vi",
        "input": "Giải thích nội dung bằng dữ kiện đã cho.",
        "reference_context": [
            {"source_id": "source-001", "content": "Dữ kiện an toàn để đánh giá."}
        ],
        "expected_answer": "Câu trả lời dựa trên dữ kiện an toàn.",
        "rubric": [],
        "required_source_ids": ["source-001"],
        "injection_label": "none",
        "sensitivity": "public",
    }


def _write_jsonl(path: Path, cases: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )


def _complete_cases() -> list[dict]:
    cases: list[dict] = []
    for use_case, count in EXPECTED_COMPLETE_DISTRIBUTION.items():
        for index in range(1, count + 1):
            cases.append(_case(f"{use_case.replace('_', '-')}-{index:03d}", use_case))
    return cases


def _manifest(fingerprint: str) -> GoldenDatasetApprovalManifest:
    return GoldenDatasetApprovalManifest.model_validate(
        {
            "schema_version": "1.0",
            "dataset_sha256": fingerprint,
            "approval_source": "owner",
            "approved_by": "project-owner",
            "approved_at": "2026-08-28T12:00:00+07:00",
            "approval_version": "ai-006-v1",
        }
    )


def test_structure_validation_has_deterministic_order_independent_fingerprint(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    cases = [_case("rag-002"), _case("rag-001")]
    _write_jsonl(first_path, cases)
    _write_jsonl(second_path, list(reversed(cases)))

    first = load_golden_dataset(
        first_path, require_complete=False, require_approval=False
    )
    second = load_golden_dataset(
        second_path, require_complete=False, require_approval=False
    )

    assert first.fingerprint_sha256 == second.fingerprint_sha256
    assert first.approval_verified is False
    assert first.approval is None


def test_exact_manifest_fingerprint_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    _write_jsonl(path, _complete_cases())
    draft = load_golden_dataset(path, require_approval=False)

    approved = load_golden_dataset(
        path,
        approval_manifest=_manifest(draft.fingerprint_sha256),
    )

    assert approved.approval_verified is True
    assert approved.approval is not None
    assert approved.approval.dataset_sha256 == draft.fingerprint_sha256


def test_content_change_invalidates_manifest(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    cases = _complete_cases()
    _write_jsonl(path, cases)
    draft = load_golden_dataset(path, require_approval=False)
    cases[0]["expected_answer"] = "Nội dung đã bị thay đổi."
    _write_jsonl(path, cases)

    with pytest.raises(GoldenDatasetValidationError, match="does not match"):
        load_golden_dataset(
            path,
            approval_manifest=_manifest(draft.fingerprint_sha256),
        )


def test_approval_manifest_is_required_by_default(tmp_path: Path) -> None:
    path = tmp_path / "dataset.jsonl"
    _write_jsonl(path, _complete_cases())

    with pytest.raises(GoldenDatasetValidationError, match="manifest is required"):
        load_golden_dataset(path)


def test_library_never_approves_a_partial_dataset(tmp_path: Path) -> None:
    path = tmp_path / "partial.jsonl"
    _write_jsonl(path, [_case()])

    with pytest.raises(GoldenDatasetValidationError, match="complete 40-case"):
        load_golden_dataset(
            path,
            require_complete=False,
            approval_manifest=_manifest("0" * 64),
        )


@pytest.mark.parametrize(
    ("manifest", "error_type"),
    [
        ({}, "missing"),
        (
            {
                "schema_version": "1.0",
                "dataset_sha256": "A" * 64,
                "approval_source": "owner",
                "approved_by": "project-owner",
                "approved_at": "2026-08-28T12:00:00+07:00",
                "approval_version": "ai-006-v1",
            },
            "string_pattern_mismatch",
        ),
        (
            {
                "schema_version": "1.0",
                "dataset_sha256": "0" * 64,
                "approval_source": "owner",
                "approved_by": "project-owner",
                "approved_at": "2026-08-28T12:00:00",
                "approval_version": "ai-006-v1",
            },
            "timezone_aware",
        ),
    ],
)
def test_invalid_manifest_is_rejected_safely(
    tmp_path: Path, manifest: dict, error_type: str
) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(GoldenDatasetValidationError, match=error_type):
        load_approval_manifest(path)


def test_manifest_invalid_json_and_extra_fields_are_rejected(tmp_path: Path) -> None:
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{not-json}", encoding="utf-8")
    with pytest.raises(GoldenDatasetValidationError, match="invalid JSON"):
        load_approval_manifest(invalid_json)

    extra = tmp_path / "extra.json"
    raw_manifest = _manifest("0" * 64).model_dump(mode="json")
    raw_manifest["signature"] = "not-supported"
    extra.write_text(json.dumps(raw_manifest), encoding="utf-8")
    with pytest.raises(GoldenDatasetValidationError, match="extra_forbidden"):
        load_approval_manifest(extra)


def test_complete_distribution_is_enforced(tmp_path: Path) -> None:
    path = tmp_path / "complete.jsonl"
    _write_jsonl(path, _complete_cases())

    dataset = load_golden_dataset(path, require_approval=False)

    assert len(dataset.cases) == 40
    assert dataset.distribution == EXPECTED_COMPLETE_DISTRIBUTION


def test_incomplete_distribution_reports_counts_without_payload(tmp_path: Path) -> None:
    path = tmp_path / "partial.jsonl"
    _write_jsonl(path, [_case()])

    with pytest.raises(GoldenDatasetValidationError, match="rag_chat=1") as error:
        load_golden_dataset(path, require_approval=False)

    assert "Giải thích" not in str(error.value)
    assert str(path) not in str(error.value)


def test_duplicate_case_id_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.jsonl"
    _write_jsonl(path, [_case(), _case()])

    with pytest.raises(GoldenDatasetValidationError, match="duplicate case IDs"):
        load_golden_dataset(path, require_complete=False, require_approval=False)


@pytest.mark.parametrize(
    ("mutate", "error_type"),
    [
        (lambda case: case.update(extra="not-allowed"), "extra_forbidden"),
        (lambda case: case.update(expected_answer=None), "value_error"),
        (
            lambda case: case["required_source_ids"].append("unknown-source"),
            "value_error",
        ),
        (
            lambda case: case["reference_context"].append(
                {"source_id": "source-001", "content": "duplicate"}
            ),
            "value_error",
        ),
        (
            lambda case: case.update(
                rubric=[
                    {"criterion_id": "first", "description": "First", "weight": 0.4},
                    {"criterion_id": "second", "description": "Second", "weight": 0.4},
                ]
            ),
            "value_error",
        ),
    ],
)
def test_invalid_case_contract_is_rejected(
    tmp_path: Path, mutate, error_type: str
) -> None:
    case = _case()
    mutate(case)
    path = tmp_path / "invalid.jsonl"
    _write_jsonl(path, [case])

    with pytest.raises(GoldenDatasetValidationError, match=error_type):
        load_golden_dataset(path, require_complete=False, require_approval=False)


def test_rubric_can_replace_expected_answer(tmp_path: Path) -> None:
    case = _case()
    case["expected_answer"] = None
    case["rubric"] = [
        {
            "criterion_id": "grounded",
            "description": "Uses the supplied source.",
            "weight": 1.0,
        }
    ]
    path = tmp_path / "rubric.jsonl"
    _write_jsonl(path, [case])

    dataset = load_golden_dataset(
        path, require_complete=False, require_approval=False
    )

    assert len(dataset.cases[0].rubric) == 1


def test_secret_scanning_covers_identifier_fields(tmp_path: Path) -> None:
    secret = "github_pat_abcdefghijklmnopqrstuvwxyz1234567890"
    case = _case()
    case["case_id"] = secret
    path = tmp_path / "identifier-secret.jsonl"
    _write_jsonl(path, [case])

    with pytest.raises(GoldenDatasetValidationError) as error:
        load_golden_dataset(path, require_complete=False, require_approval=False)

    assert secret not in str(error.value)


@pytest.mark.parametrize(
    "secret",
    [
        "api_key=abcdefghijklmnop",
        "postgresql://user:password@localhost/database",
        "-----BEGIN PRIVATE KEY-----",
        "Bearer abcdefghijklmnopqrstuvwxyz",
    ],
)
def test_secret_like_content_is_rejected_without_echo(tmp_path: Path, secret: str) -> None:
    case = _case()
    case["input"] = secret
    path = tmp_path / "secret.jsonl"
    _write_jsonl(path, [case])

    with pytest.raises(GoldenDatasetValidationError) as error:
        load_golden_dataset(path, require_complete=False, require_approval=False)

    assert secret not in str(error.value)
    assert str(path) not in str(error.value)


def test_missing_and_invalid_files_have_safe_errors(tmp_path: Path) -> None:
    missing = tmp_path / "private" / "missing.jsonl"
    with pytest.raises(GoldenDatasetValidationError, match="file does not exist") as error:
        load_golden_dataset(missing, require_approval=False)
    assert str(missing) not in str(error.value)

    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(GoldenDatasetValidationError, match="invalid JSON"):
        load_golden_dataset(invalid, require_approval=False)

    invalid_utf8 = tmp_path / "invalid-utf8.jsonl"
    invalid_utf8.write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(GoldenDatasetValidationError, match="not valid UTF-8"):
        load_golden_dataset(invalid_utf8, require_approval=False)


def test_structure_only_cli_reports_fingerprint_without_approval(
    tmp_path: Path, capsys
) -> None:
    path = tmp_path / "complete.jsonl"
    _write_jsonl(path, _complete_cases())

    assert main([str(path), "--structure-only"]) == 0

    output = capsys.readouterr().out
    assert "AI_GOLDEN_DATASET_STRUCTURE_OK" in output
    assert "approval_record_matched=false" in output
    assert "cases=40" in output


def test_cli_requires_manifest_for_final_validation(tmp_path: Path, capsys) -> None:
    path = tmp_path / "complete.jsonl"
    _write_jsonl(path, _complete_cases())

    assert main([str(path)]) == 1

    output = capsys.readouterr().out
    assert "--approval-manifest is required" in output
    assert str(path) not in output


def test_cli_never_approves_partial_dataset(tmp_path: Path, capsys) -> None:
    dataset_path = tmp_path / "partial.jsonl"
    manifest_path = tmp_path / "approval.json"
    _write_jsonl(dataset_path, [_case()])
    draft = load_golden_dataset(
        dataset_path, require_complete=False, require_approval=False
    )
    manifest_path.write_text(
        json.dumps(_manifest(draft.fingerprint_sha256).model_dump(mode="json")),
        encoding="utf-8",
    )

    assert main(
        [
            str(dataset_path),
            "--allow-partial",
            "--approval-manifest",
            str(manifest_path),
        ]
    ) == 1

    output = capsys.readouterr().out
    assert "--allow-partial is valid only with --structure-only" in output
    assert "AI_GOLDEN_DATASET_OK" not in output


def test_cli_accepts_matching_manifest(tmp_path: Path, capsys) -> None:
    dataset_path = tmp_path / "complete.jsonl"
    manifest_path = tmp_path / "approval.json"
    _write_jsonl(dataset_path, _complete_cases())
    draft = load_golden_dataset(
        dataset_path, require_complete=True, require_approval=False
    )
    manifest_path.write_text(
        json.dumps(_manifest(draft.fingerprint_sha256).model_dump(mode="json")),
        encoding="utf-8",
    )

    assert main(
        [str(dataset_path), "--approval-manifest", str(manifest_path)]
    ) == 0

    output = capsys.readouterr().out
    assert "AI_GOLDEN_DATASET_OK" in output
    assert "approval_record_matched=true" in output
    assert draft.fingerprint_sha256 in output


def test_cli_rejects_mismatched_manifest_without_payload(tmp_path: Path, capsys) -> None:
    dataset_path = tmp_path / "complete.jsonl"
    manifest_path = tmp_path / "approval.json"
    cases = _complete_cases()
    _write_jsonl(dataset_path, cases)
    draft = load_golden_dataset(
        dataset_path, require_complete=True, require_approval=False
    )
    manifest_path.write_text(
        json.dumps(_manifest(draft.fingerprint_sha256).model_dump(mode="json")),
        encoding="utf-8",
    )
    changed = deepcopy(cases)
    changed[0]["expected_answer"] = "Tampered content"
    _write_jsonl(dataset_path, changed)

    assert main(
        [str(dataset_path), "--approval-manifest", str(manifest_path)]
    ) == 1

    output = capsys.readouterr().out
    assert "AI_GOLDEN_DATASET_INVALID" in output
    assert "Tampered content" not in output
    assert str(dataset_path) not in output
