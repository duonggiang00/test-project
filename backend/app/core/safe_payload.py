from __future__ import annotations

import ipaddress
import json
import math
import re
from typing import AbstractSet, Any

from pydantic import JsonValue


class UnsafeStructuredPayloadError(ValueError):
    """Raised when a structured payload cannot be serialized safely."""


_SAFE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_SEPARATOR = re.compile(r"[^a-zA-Z0-9]+")

_SENSITIVE_SINGLE_KEY_TOKENS = {
    "authorization",
    "cookie",
    "credentials",
    "credential",
    "email",
    "filename",
    "filepath",
    "fullname",
    "password",
    "passwd",
    "path",
    "pwd",
    "secret",
    "token",
    "useragent",
    "username",
}
_SENSITIVE_TOKEN_QUALIFIERS = {
    "access",
    "auth",
    "csrf",
    "id",
    "refresh",
    "session",
}
_RAW_VALUE_QUALIFIERS = {
    "body",
    "content",
    "data",
    "payload",
    "raw",
    "retrieved",
    "text",
    "value",
}
_SENSITIVE_NORMALIZED_KEY_FRAGMENTS = {
    "authorization",
    "cookie",
    "credential",
    "email",
    "filename",
    "filepath",
    "fullname",
    "passwd",
    "password",
    "secret",
    "useragent",
    "username",
}
_SENSITIVE_NORMALIZED_KEYS = {
    "accesstoken",
    "apikey",
    "authtoken",
    "clientip",
    "clientsecret",
    "csrftoken",
    "idtoken",
    "ip",
    "ipaddress",
    "path",
    "providererror",
    "refreshtoken",
    "remoteaddress",
    "remoteip",
    "sessiontoken",
    "token",
    "tokens",
}

_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+"),
    re.compile(r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b"),
    re.compile(r"\bsk-[a-zA-Z0-9_-]{8,}\b"),
    re.compile(r"(?i)-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"(?i)https?://[^/\s:@]+:[^@\s/]+@"),
    re.compile(r"(?i)\b(?:session|token|auth|cookie)[_-]?[a-z0-9]*=[^;\s]+"),
    re.compile(r"\b[A-Za-z]:\\[^\r\n]+"),
    re.compile(r"(?:^|\s)\\\\[^\\\s]+\\[^\r\n]+"),
    re.compile(r"(?i)\bfile://[^\s]+"),
    re.compile(
        r"(?i)(?<![:\w])/(?:app|etc|home|mnt|opt|private|root|srv|tmp|users|workspace)(?:/|$)"
    ),
    re.compile(r"(?:^|\s)/(?:[^/\s]+/)*[^/\s]*"),
    re.compile(r"(?:^|[\\/])\.\.(?:[\\/]|$)"),
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    re.compile(r"(?i)\b(?:mozilla|postmanruntime|curl|wget)/[0-9]"),
)
_IPV4_CANDIDATE = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
_IP_TOKEN_SEPARATOR = re.compile(r"[\s=,;(){}<>]+")


def _key_tokens(key: str) -> tuple[str, ...]:
    with_boundaries = _CAMEL_CASE_BOUNDARY.sub("_", key)
    return tuple(
        token.casefold()
        for token in _KEY_SEPARATOR.split(with_boundaries)
        if token
    )


def _has_normalized_raw_subject(normalized: str, subject: str) -> bool:
    prefixes = ("raw", "retrieved")
    suffixes = ("body", "content", "data", "payload", "raw", "retrieved", "text", "value")
    return normalized.startswith(
        tuple(f"{prefix}{subject}" for prefix in prefixes)
    ) or normalized.startswith(
        tuple(f"{subject}{suffix}" for suffix in suffixes)
    )


def _is_sensitive_key(key: str) -> bool:
    tokens = _key_tokens(key)
    token_set = set(tokens)
    normalized = "".join(tokens)

    if token_set & _SENSITIVE_SINGLE_KEY_TOKENS:
        return True
    if normalized in _SENSITIVE_NORMALIZED_KEYS:
        return True
    if any(
        fragment in normalized
        for fragment in _SENSITIVE_NORMALIZED_KEY_FRAGMENTS
    ):
        return True
    if "tokens" in token_set and token_set & _SENSITIVE_TOKEN_QUALIFIERS:
        return True
    if (
        "provider" in token_set and "error" in token_set
    ) or normalized == "providererror":
        return True
    if "actor" in token_set and token_set & {"email", "name"}:
        return True
    if "document" in token_set and token_set & _RAW_VALUE_QUALIFIERS:
        return True
    if _has_normalized_raw_subject(normalized, "document"):
        return True
    if "prompt" in token_set and (
        len(tokens) == 1 or token_set & _RAW_VALUE_QUALIFIERS
    ):
        return True
    if _has_normalized_raw_subject(normalized, "prompt"):
        return True
    if "context" in token_set and (
        len(tokens) == 1 or token_set & _RAW_VALUE_QUALIFIERS
    ):
        return True
    if _has_normalized_raw_subject(normalized, "context"):
        return True
    if token_set & {"request", "response"} and token_set & {"body", "payload"}:
        return True
    if any(
        subject in normalized for subject in ("request", "response")
    ) and any(
        qualifier in normalized for qualifier in ("body", "payload")
    ):
        return True
    if "ip" in token_set and (
        len(tokens) == 1 or token_set & {"address", "client", "remote"}
    ):
        return True
    if "address" in token_set and token_set & {"client", "remote"}:
        return True
    if normalized in {"clientip", "remoteip", "ipaddress", "remoteaddress"}:
        return True
    return False


def _contains_ip_address(value: str) -> bool:
    stripped = value.strip("[](){}<>,; ")
    try:
        ipaddress.ip_address(stripped)
        return True
    except ValueError:
        pass

    for token in _IP_TOKEN_SEPARATOR.split(value):
        candidate = token.strip("[]'\"")
        if not candidate:
            continue
        try:
            ipaddress.ip_address(candidate)
            return True
        except ValueError:
            continue

    for match in _IPV4_CANDIDATE.finditer(value):
        try:
            ipaddress.ip_address(match.group(0))
            return True
        except ValueError:
            continue
    return False


def _contains_sensitive_value(value: str) -> bool:
    if any(ord(character) < 32 for character in value):
        return True
    if any(pattern.search(value) for pattern in _SENSITIVE_VALUE_PATTERNS):
        return True
    return _contains_ip_address(value)


def _validate_json_value(
    value: Any,
    *,
    depth: int,
    seen: set[int],
    max_depth: int,
    max_collection_items: int,
) -> JsonValue:
    if depth > max_depth:
        raise UnsafeStructuredPayloadError(
            "Structured payload exceeds maximum nesting depth"
        )
    if isinstance(value, dict):
        if id(value) in seen:
            raise UnsafeStructuredPayloadError("Structured payload contains a cyclic value")
        if len(value) > max_collection_items:
            raise UnsafeStructuredPayloadError(
                "Structured payload contains too many object fields"
            )
        seen.add(id(value))
        validated: dict[str, JsonValue] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise UnsafeStructuredPayloadError(
                    "Structured payload contains a non-string field name"
                )
            if _is_sensitive_key(key):
                raise UnsafeStructuredPayloadError(
                    "Structured payload contains a forbidden field"
                )
            if not _SAFE_KEY_PATTERN.fullmatch(key):
                raise UnsafeStructuredPayloadError(
                    "Structured payload contains an invalid field name"
                )
            validated[key] = _validate_json_value(
                nested_value,
                depth=depth + 1,
                seen=seen,
                max_depth=max_depth,
                max_collection_items=max_collection_items,
            )
        seen.remove(id(value))
        return validated
    if isinstance(value, list):
        if id(value) in seen:
            raise UnsafeStructuredPayloadError("Structured payload contains a cyclic value")
        if len(value) > max_collection_items:
            raise UnsafeStructuredPayloadError(
                "Structured payload contains too many array items"
            )
        seen.add(id(value))
        validated_list = [
            _validate_json_value(
                item,
                depth=depth + 1,
                seen=seen,
                max_depth=max_depth,
                max_collection_items=max_collection_items,
            )
            for item in value
        ]
        seen.remove(id(value))
        return validated_list
    if isinstance(value, str):
        if _contains_sensitive_value(value):
            raise UnsafeStructuredPayloadError(
                "Structured payload contains a forbidden value"
            )
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise UnsafeStructuredPayloadError(
                "Structured payload contains a non-finite number"
            )
        return value
    if value is None or isinstance(value, (bool, int)):
        return value
    raise UnsafeStructuredPayloadError("Structured payload contains a non-JSON value")


def validate_safe_mapping(
    payload: object,
    *,
    allowed_top_level_fields: AbstractSet[str] | None,
    max_serialized_bytes: int,
    max_depth: int = 12,
    max_collection_items: int = 100,
) -> dict[str, JsonValue]:
    if not isinstance(payload, dict):
        raise UnsafeStructuredPayloadError("Structured payload must be an object")
    if not all(isinstance(key, str) for key in payload):
        raise UnsafeStructuredPayloadError(
            "Structured payload contains a non-string field name"
        )
    if allowed_top_level_fields is not None and not set(payload).issubset(
        allowed_top_level_fields
    ):
        raise UnsafeStructuredPayloadError(
            "Structured payload contains a field outside its allowlist"
        )

    validated = _validate_json_value(
        payload,
        depth=0,
        seen=set(),
        max_depth=max_depth,
        max_collection_items=max_collection_items,
    )
    if not isinstance(validated, dict):
        raise UnsafeStructuredPayloadError("Structured payload must be an object")
    encoded = json.dumps(
        validated,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(encoded) > max_serialized_bytes:
        raise UnsafeStructuredPayloadError(
            "Structured payload exceeds maximum serialized size"
        )
    return validated
