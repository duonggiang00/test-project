"""Validation at the AI question-draft publication boundary."""

import pytest
from pydantic import ValidationError

from app.schemas.ai_generation import QuestionDraft


def _metadata(count: int) -> dict:
    return {
        "blanks": [
            {
                "blank_index": index,
                "acceptable_answers": [f"answer-{index}"],
            }
            for index in range(count)
        ]
    }


@pytest.mark.unit
def test_valid_canonical_fill_draft_is_accepted() -> None:
    draft = QuestionDraft.model_validate(
        {
            "type": "FILL_IN_BLANK",
            "content": "First [BLANK], then [BLANK].",
            "metadata_json": _metadata(2),
        }
    )

    assert draft.content.count("[BLANK]") == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("content", "blank_count"),
    [
        ("No canonical token.", 1),
        ("Only one [BLANK].", 2),
        ("Canonical [BLANK] plus legacy ___.", 1),
    ],
)
def test_invalid_fill_draft_token_contract_is_rejected(
    content: str,
    blank_count: int,
) -> None:
    with pytest.raises(ValidationError):
        QuestionDraft.model_validate(
            {
                "type": "FILL_IN_BLANK",
                "content": content,
                "metadata_json": _metadata(blank_count),
            }
        )
