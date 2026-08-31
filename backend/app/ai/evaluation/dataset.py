from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from collections import Counter
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


UseCase = Literal[
    "rag_chat",
    "question_generation",
    "flashcard_generation",
    "topic_brief_generation",
]

GOLDEN_DATASET_SCHEMA_VERSION: Literal["1.0"] = "1.0"
TRUST_ROOT_SHA256_ENV = "AI_GOLDEN_DATASET_TRUST_ROOT_SHA256"
EXPECTED_COMPLETE_DISTRIBUTION: dict[UseCase, int] = {
    "rag_chat": 16,
    "question_generation": 12,
    "flashcard_generation": 6,
    "topic_brief_generation": 6,
}

_IDENTIFIER_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,79}$"
_BASE64_PATTERN = r"^[A-Za-z0-9+/]+={0,2}$"
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{16,}\b", re.IGNORECASE),
    re.compile(
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://"
        r"[^:\s/@]+:[^@\s/]+@",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:api[_-]?key|client[_-]?secret|password|token)\s*[:=]\s*"
        r"(?!<[^>]+>|\$\{[^}]+\}|REDACTED\b)[^\s,;]{8,}",
        re.IGNORECASE,
    ),
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContextSource(StrictModel):
    source_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    content: str = Field(min_length=1, max_length=20_000)


class RubricCriterion(StrictModel):
    criterion_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    description: str = Field(min_length=1, max_length=2_000)
    weight: float = Field(gt=0, le=1)


class ApprovalMetadata(StrictModel):
    approval_source: Literal["owner", "admin"]
    approved_by: str = Field(pattern=_IDENTIFIER_PATTERN)
    approved_at: AwareDatetime
    approval_version: str = Field(pattern=_IDENTIFIER_PATTERN)
    key_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    signature_base64: str = Field(pattern=_BASE64_PATTERN, min_length=86, max_length=88)

    @field_validator("signature_base64")
    @classmethod
    def validate_signature_size(cls, value: str) -> str:
        if len(_decode_base64(value, "approval signature")) != 64:
            raise ValueError("approval signature must be a 64-byte Ed25519 signature")
        return value


class TrustedApprover(StrictModel):
    key_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    approval_source: Literal["owner", "admin"]
    approved_by: str = Field(pattern=_IDENTIFIER_PATTERN)
    public_key_base64: str = Field(pattern=_BASE64_PATTERN, min_length=43, max_length=44)

    @field_validator("public_key_base64")
    @classmethod
    def validate_public_key_size(cls, value: str) -> str:
        if len(_decode_base64(value, "approver public key")) != 32:
            raise ValueError("approver public key must be a 32-byte Ed25519 key")
        return value


class TrustedApproverStore(StrictModel):
    schema_version: Literal["1.0"]
    approvers: list[TrustedApprover] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_unique_keys(self) -> "TrustedApproverStore":
        duplicate_keys = _duplicates([approver.key_id for approver in self.approvers])
        if duplicate_keys:
            raise ValueError(f"duplicate trusted key IDs: {', '.join(duplicate_keys)}")
        return self


class GoldenDatasetCase(StrictModel):
    schema_version: Literal["1.0"]
    case_id: str = Field(pattern=_IDENTIFIER_PATTERN)
    use_case: UseCase
    language: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    input: str = Field(min_length=1, max_length=20_000)
    reference_context: list[ContextSource] = Field(max_length=50)
    expected_answer: str | None = Field(default=None, min_length=1, max_length=20_000)
    rubric: list[RubricCriterion] = Field(default_factory=list, max_length=50)
    required_source_ids: list[str] = Field(max_length=50)
    injection_label: Literal["none", "direct", "indirect"]
    sensitivity: Literal["public", "internal", "personal", "sensitive"]
    approval: ApprovalMetadata

    @model_validator(mode="after")
    def validate_reference_contract(self) -> "GoldenDatasetCase":
        if self.expected_answer is None and not self.rubric:
            raise ValueError("expected_answer or rubric is required")

        source_ids = [source.source_id for source in self.reference_context]
        duplicate_sources = _duplicates(source_ids)
        if duplicate_sources:
            raise ValueError(f"duplicate source IDs: {', '.join(duplicate_sources)}")

        duplicate_required = _duplicates(self.required_source_ids)
        if duplicate_required:
            raise ValueError(
                f"duplicate required source IDs: {', '.join(duplicate_required)}"
            )

        unknown_sources = sorted(set(self.required_source_ids) - set(source_ids))
        if unknown_sources:
            raise ValueError(f"unknown required source IDs: {', '.join(unknown_sources)}")

        criterion_ids = [criterion.criterion_id for criterion in self.rubric]
        duplicate_criteria = _duplicates(criterion_ids)
        if duplicate_criteria:
            raise ValueError(f"duplicate rubric criterion IDs: {', '.join(duplicate_criteria)}")
        if self.rubric and abs(sum(item.weight for item in self.rubric) - 1.0) > 1e-9:
            raise ValueError("rubric weights must sum to 1.0")

        secret_location = _find_secret_location(self)
        if secret_location is not None:
            raise ValueError(f"raw secret-like content is not allowed in {secret_location}")
        return self


class GoldenDataset(StrictModel):
    schema_version: Literal["1.0"]
    cases: list[GoldenDatasetCase]
    fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approvals_verified: bool
    trust_root_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @property
    def distribution(self) -> dict[str, int]:
        counts: Counter[UseCase] = Counter(case.use_case for case in self.cases)
        return {key: counts.get(key, 0) for key in EXPECTED_COMPLETE_DISTRIBUTION}


class GoldenDatasetValidationError(ValueError):
    """A safe validation failure that never contains raw case payloads or paths."""


def load_trusted_approvers(path: Path) -> TrustedApproverStore:
    raw_text = _read_safe_text(path, "trusted approver store")
    try:
        raw_store = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GoldenDatasetValidationError(
            f"trusted approver store contains invalid JSON ({exc.msg})"
        ) from None
    try:
        return TrustedApproverStore.model_validate(raw_store)
    except ValueError as exc:
        raise GoldenDatasetValidationError(
            f"trusted approver store validation failed ({_first_validation_error_type(exc)})"
        ) from None


def trusted_approver_store_fingerprint(store: TrustedApproverStore) -> str:
    canonical = json.dumps(
        store.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def approval_signing_payload(case: GoldenDatasetCase) -> bytes:
    payload = case.model_dump(mode="json")
    del payload["approval"]["signature_base64"]
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def load_golden_dataset(
    path: Path,
    *,
    require_complete: bool = True,
    trust_store: TrustedApproverStore | None = None,
    trusted_root_sha256: str | None = None,
    require_trusted_approval: bool = True,
) -> GoldenDataset:
    raw_text = _read_safe_text(path, "dataset")
    cases: list[GoldenDatasetCase] = []
    for line_number, raw_line in enumerate(raw_text.splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            raw_case = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise GoldenDatasetValidationError(
                f"line {line_number}: invalid JSON ({exc.msg})"
            ) from None
        try:
            cases.append(GoldenDatasetCase.model_validate(raw_case))
        except ValueError as exc:
            raise GoldenDatasetValidationError(
                f"line {line_number}: case validation failed "
                f"({_first_validation_error_type(exc)})"
            ) from None

    if not cases:
        raise GoldenDatasetValidationError("dataset contains no cases")

    duplicate_cases = _duplicates([case.case_id for case in cases])
    if duplicate_cases:
        raise GoldenDatasetValidationError(
            f"duplicate case IDs: {', '.join(duplicate_cases)}"
        )

    if require_trusted_approval:
        if trust_store is None or trusted_root_sha256 is None:
            raise GoldenDatasetValidationError(
                "owner-pinned trusted approval verification is required"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", trusted_root_sha256):
            raise GoldenDatasetValidationError("trusted approval root fingerprint is invalid")
        actual_trust_root = trusted_approver_store_fingerprint(trust_store)
        if not hmac.compare_digest(actual_trust_root, trusted_root_sha256):
            raise GoldenDatasetValidationError(
                "trusted approver store does not match the owner-pinned root"
            )
        _verify_approvals(cases, trust_store)

    distribution: Counter[UseCase] = Counter(case.use_case for case in cases)
    if require_complete:
        actual = {key: distribution.get(key, 0) for key in EXPECTED_COMPLETE_DISTRIBUTION}
        if actual != EXPECTED_COMPLETE_DISTRIBUTION:
            expected_text = _format_distribution(EXPECTED_COMPLETE_DISTRIBUTION)
            actual_text = _format_distribution(actual)
            raise GoldenDatasetValidationError(
                f"complete dataset requires {expected_text}; found {actual_text}"
            )

    canonical_lines = [
        json.dumps(case.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for case in sorted(cases, key=lambda item: item.case_id)
    ]
    fingerprint = hashlib.sha256(("\n".join(canonical_lines) + "\n").encode()).hexdigest()
    return GoldenDataset(
        schema_version=GOLDEN_DATASET_SCHEMA_VERSION,
        cases=cases,
        fingerprint_sha256=fingerprint,
        approvals_verified=require_trusted_approval,
        trust_root_sha256=trusted_root_sha256 if require_trusted_approval else None,
    )


def _verify_approvals(
    cases: list[GoldenDatasetCase],
    trust_store: TrustedApproverStore,
) -> None:
    approvers = {approver.key_id: approver for approver in trust_store.approvers}
    for case in cases:
        approval = case.approval
        approver = approvers.get(approval.key_id)
        if approver is None:
            raise GoldenDatasetValidationError(
                f"case {case.case_id}: approval key is not trusted"
            )
        if (
            approver.approved_by != approval.approved_by
            or approver.approval_source != approval.approval_source
        ):
            raise GoldenDatasetValidationError(
                f"case {case.case_id}: approval identity does not match trusted key"
            )
        public_key = Ed25519PublicKey.from_public_bytes(
            _decode_base64(approver.public_key_base64, "approver public key")
        )
        try:
            public_key.verify(
                _decode_base64(approval.signature_base64, "approval signature"),
                approval_signing_payload(case),
            )
        except InvalidSignature:
            raise GoldenDatasetValidationError(
                f"case {case.case_id}: approval signature is invalid"
            ) from None


def _read_safe_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise GoldenDatasetValidationError(f"{label} file does not exist") from None
    except (IsADirectoryError, PermissionError, OSError):
        raise GoldenDatasetValidationError(f"{label} file could not be read") from None
    except UnicodeError:
        raise GoldenDatasetValidationError(f"{label} file is not valid UTF-8") from None


def _decode_base64(value: str, label: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError(f"{label} must use canonical base64") from None


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def _find_secret_location(case: GoldenDatasetCase) -> str | None:
    for location, value in _iter_string_fields(case.model_dump(mode="json")):
        if location == "approval.signature_base64":
            continue
        if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
            return location
    return None


def _iter_string_fields(value: object, prefix: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, nested in value.items():
            location = f"{prefix}.{key}" if prefix else str(key)
            yield from _iter_string_fields(nested, location)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            location = f"{prefix}.{index}" if prefix else str(index)
            yield from _iter_string_fields(nested, location)


def _first_validation_error_type(error: ValueError) -> str:
    errors_method = getattr(error, "errors", None)
    if callable(errors_method):
        errors = errors_method()
        if errors:
            return str(errors[0].get("type", "invalid_case"))
    return "invalid_case"


def _format_distribution(distribution: Mapping[UseCase, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in distribution.items())
