"""Versioned prompt templates (AI-001).

Each module exposes a stable `PROMPT_ID`, an integer `PROMPT_VERSION`, and a
`render(...)` function. Wording is unchanged from the inline f-strings that
used to live in `ai_studio_service.py`/`material_service.py` -- this package
only extracts and versions them, it does not edit prompt content.

`prompt_version_label` renders that pair into the single stable string the
audit contract asks for (AI-003).
"""
from __future__ import annotations

from typing import Protocol


class VersionedPrompt(Protocol):
    """The shape every prompt module in this package satisfies."""

    PROMPT_ID: str
    PROMPT_VERSION: int


def prompt_version_label(prompt: VersionedPrompt) -> str:
    """`"question_generation-v1"`.

    `ERROR_AND_AUDIT_CONTRACTS.md` §2.4 specifies `prompt_version` as a
    single string of exactly this shape (its example is
    `"exam-generation-v3"`), so the id and the integer version are joined
    here once rather than at each of the three generation call sites.
    Changing a prompt's wording means bumping `PROMPT_VERSION`, which
    changes this label, which is what makes "Prompt/model changes become
    measurable governed changes" (ADR-0006) true in the audit trail.
    """
    return f"{prompt.PROMPT_ID}-v{prompt.PROMPT_VERSION}"
