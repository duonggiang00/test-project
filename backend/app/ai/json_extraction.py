"""Shared parsing for LLM completions that must return JSON.

Extracted from `MaterialService`, where this exact logic was duplicated
across `generate_questions`, `generate_flashcards`, and
`generate_topic_brief` (AI-001 debt called out in
`docs/plans/AI-001-009_CHANGE_CONTRACT.md`). Behavior is unchanged: strip a
markdown code fence if present, otherwise fall back to slicing between the
first `{`/`[` and the matching last `}`/`]`, then `json.loads` the result.
"""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE_PATTERN = re.compile(r"```(?:json)?(.*?)```", re.DOTALL)


def extract_json_payload(content: str) -> Any:
    """Parse a JSON object/array out of raw LLM text.

    Raises `json.JSONDecodeError` (the same exception `json.loads` raises)
    when no valid JSON payload can be recovered, so existing callers can
    keep catching that specific type.
    """
    text = content.strip()

    match = _FENCE_PATTERN.search(text)
    if match:
        text = match.group(1).strip()
    else:
        first_brace = text.find("{")
        first_bracket = text.find("[")
        start_idx = -1
        if first_brace != -1 and first_bracket != -1:
            start_idx = min(first_brace, first_bracket)
        elif first_brace != -1:
            start_idx = first_brace
        elif first_bracket != -1:
            start_idx = first_bracket

        if start_idx != -1:
            if text[start_idx] == "{":
                end_idx = text.rfind("}")
            else:
                end_idx = text.rfind("]")

            if end_idx != -1:
                text = text[start_idx : end_idx + 1]

    return json.loads(text)
