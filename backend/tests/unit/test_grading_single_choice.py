"""Deterministic grading of `SINGLE_CHOICE` questions.

`SINGLE_CHOICE` reached the schema and the question bank in DATA-DEMO-001
(migration `a83c1d7e9f02`) but `GradingService.grade_question` had no branch
for it, so it fell through to the `return 0.0` default: a student who
answered a single-choice question correctly scored zero. The demo dataset
carries 24 such questions, which is why its handoff recorded "published demo
exams therefore contain only currently gradeable types" as a known gap.

These tests pin the branch and, more importantly, the places where it is
deliberately *stricter* than `grade_multiple_choice` -- a single-choice
question asks for one answer, so a two-option payload is malformed input
rather than partial credit.
"""

import uuid

import pytest

from app.models.enums import QuestionType
from app.models.exam import Option, Question
from app.services.grading_service import GradingService


def _question(*, correct_count=1, option_count=4, points=10):
    """A `SINGLE_CHOICE` question with explicit option ids.

    Ids are assigned by hand because these objects are never flushed --
    SQLAlchemy's `default=uuid.uuid4` only fires at insert time, so an
    unflushed `Option.id` is `None` and would make every comparison here
    accidentally pass or fail for the wrong reason.
    """
    question = Question(
        question_type=QuestionType.SINGLE_CHOICE,
        content="Which one?",
        points=points,
        metadata_json={},
    )
    question.options = [
        Option(id=uuid.uuid4(), content=f"Option {i}", is_correct=i < correct_count)
        for i in range(option_count)
    ]
    return question


def _correct_id(question):
    return str(next(opt.id for opt in question.options if opt.is_correct))


def _wrong_id(question):
    return str(next(opt.id for opt in question.options if not opt.is_correct))


@pytest.mark.unit
def test_correct_single_choice_answer_scores_full_points():
    question = _question(points=10)
    awarded = GradingService.grade_question(
        question, {"selected_option_id": _correct_id(question)}
    )
    assert awarded == 10.0


@pytest.mark.unit
def test_wrong_single_choice_answer_scores_zero():
    question = _question()
    awarded = GradingService.grade_question(
        question, {"selected_option_id": _wrong_id(question)}
    )
    assert awarded == 0.0


@pytest.mark.unit
def test_the_list_payload_shape_is_accepted_when_it_holds_exactly_one_id():
    """`student_service` sets both keys, and older clients may send only the list."""
    question = _question(points=5)
    awarded = GradingService.grade_question(
        question, {"selected_option_ids": [_correct_id(question)]}
    )
    assert awarded == 5.0


@pytest.mark.unit
def test_selecting_two_options_scores_zero_rather_than_full_marks():
    """The core reason this is not an alias for `grade_multiple_choice`.

    Set-comparing would let a submission that picked the right option *and*
    a wrong one score full marks whenever the question happened to carry two
    correct options. A single-choice question asks for one answer; two is a
    malformed answer, not a partially right one.
    """
    question = _question()
    both = [_correct_id(question), _wrong_id(question)]
    assert GradingService.grade_question(
        question, {"selected_option_ids": both}
    ) == 0.0


@pytest.mark.unit
def test_a_question_without_exactly_one_correct_option_scores_zero():
    """A malformed question must not produce a confident grade.

    Awarding points off a broken question would put a wrong mark on a
    retained educational record, so both shapes fail closed.
    """
    no_correct = _question(correct_count=0)
    assert GradingService.grade_question(
        no_correct, {"selected_option_id": str(no_correct.options[0].id)}
    ) == 0.0

    two_correct = _question(correct_count=2)
    assert GradingService.grade_question(
        two_correct, {"selected_option_id": _correct_id(two_correct)}
    ) == 0.0


@pytest.mark.unit
@pytest.mark.parametrize(
    "answer_data",
    [
        {},
        {"selected_option_id": None},
        {"selected_option_ids": []},
        {"selected_option_ids": None},
        {"selected_option_ids": "not-a-list"},
        {"blanks": {"0": "unrelated"}},
    ],
    ids=[
        "empty",
        "explicit-null-id",
        "empty-list",
        "null-list",
        "non-list",
        "wrong-question-type-payload",
    ],
)
def test_missing_or_malformed_answers_score_zero_without_raising(answer_data):
    question = _question()
    assert GradingService.grade_question(question, answer_data) == 0.0


@pytest.mark.unit
def test_uuid_objects_and_their_strings_grade_identically():
    """`student_service` stringifies ids; a direct caller may not."""
    question = _question(points=7)
    raw_uuid = next(opt.id for opt in question.options if opt.is_correct)
    assert GradingService.grade_question(
        question, {"selected_option_id": raw_uuid}
    ) == 7.0
    assert GradingService.grade_question(
        question, {"selected_option_id": str(raw_uuid)}
    ) == 7.0


@pytest.mark.unit
def test_other_question_types_are_unaffected_by_the_new_branch():
    """The existing deterministic scoring must be untouched."""
    mc = Question(
        question_type=QuestionType.MULTIPLE_CHOICE,
        content="Pick all",
        points=6,
        metadata_json={},
    )
    mc.options = [
        Option(id=uuid.uuid4(), content="a", is_correct=True),
        Option(id=uuid.uuid4(), content="b", is_correct=True),
        Option(id=uuid.uuid4(), content="c", is_correct=False),
    ]
    correct = [str(o.id) for o in mc.options if o.is_correct]
    # Multiple choice still takes a set of ids and still needs all of them.
    assert GradingService.grade_question(
        mc, {"selected_option_ids": correct}
    ) == 6.0
    assert GradingService.grade_question(
        mc, {"selected_option_ids": correct[:1]}
    ) == 0.0
