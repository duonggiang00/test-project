"""Fail-closed grading contracts for structured Student answers."""

import pytest

from app.models.enums import QuestionType
from app.models.exam import Question
from app.services.grading_service import GradingService


def _matching_question() -> Question:
    return Question(
        question_type=QuestionType.MATCHING,
        content="Match each number.",
        points=4,
        metadata_json={
            "pairs": [
                {"left": "One", "right": "Một"},
                {"left": "Two", "right": "Hai"},
            ]
        },
    )


def _fill_question() -> Question:
    return Question(
        question_type=QuestionType.FILL_IN_BLANK,
        content="Complete [BLANK].",
        points=2,
        metadata_json={
            "blanks": [
                {"blank_index": 0, "acceptable_answers": ["answer"]},
            ]
        },
    )


@pytest.mark.unit
def test_matching_rejects_cartesian_product_answer_attack() -> None:
    question = _matching_question()
    cartesian_product = [
        {"left": left, "right": right}
        for left in ("One", "Two")
        for right in ("Một", "Hai")
    ]

    assert GradingService.grade_question(
        question,
        {"matches": cartesian_product},
    ) == 0.0


@pytest.mark.unit
@pytest.mark.parametrize(
    "matches",
    [
        "not-a-list",
        ["not-a-pair"],
        [{"left": "One", "right": "Một"}, {"left": "One", "right": "Hai"}],
        [{"left": "One", "right": "Một"}, {"left": "Two", "right": "Một"}],
        [{"left": "Unexpected", "right": "Một"}],
        [{"left": "One", "right": "Unexpected"}],
    ],
)
def test_matching_malformed_or_non_bijective_answers_score_zero(matches: object) -> None:
    assert GradingService.grade_question(
        _matching_question(),
        {"matches": matches},
    ) == 0.0


@pytest.mark.unit
def test_matching_keeps_valid_partial_credit() -> None:
    assert GradingService.grade_question(
        _matching_question(),
        {"matches": [{"left": "One", "right": "Một"}]},
    ) == 2.0


@pytest.mark.unit
@pytest.mark.parametrize(
    "blanks",
    [
        "not-an-object",
        [],
        ["answer"],
    ],
)
def test_fill_in_blank_malformed_answers_score_zero_without_raising(blanks: object) -> None:
    assert GradingService.grade_question(
        _fill_question(),
        {"blanks": blanks},
    ) == 0.0

