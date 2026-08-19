"""End-to-end grading of a `SINGLE_CHOICE` question through the real API.

The unit tests in `tests/unit/test_grading_single_choice.py` pin the grading
branch itself. This proves the whole path a student actually travels --
create a single-choice question, start the exam, submit, and be scored --
because the defect it guards against was precisely a missing branch that no
caller noticed: `grade_question` silently returned 0.0 for this type, so a
correct answer produced a wrong grade on a retained educational record.

The demo fixture cannot cover this yet: its 12 single-choice questions sit
in exams that none of its 15 submissions target, so no seeded submission
exercises the type.
"""

import uuid

import pytest

from tests.test_authorization_idor import create_exam, create_teacher, create_topic


def _single_choice_exam(client, teacher, *, points=10):
    topic = create_topic(client, teacher, f"Single choice {uuid.uuid4()}")
    exam = create_exam(
        client,
        teacher,
        f"Single choice exam {uuid.uuid4()}",
        topic_id=topic["id"],
        published=True,
    )
    question = client.post(
        f"/exams/{exam['id']}/questions",
        json={
            "content": "Thu do cua Viet Nam la?",
            "question_type": "SINGLE_CHOICE",
            "points": points,
            "options": [
                {"content": "Ha Noi", "is_correct": True},
                {"content": "Da Nang", "is_correct": False},
                {"content": "Can Tho", "is_correct": False},
            ],
        },
        headers=teacher["headers"],
    )
    assert question.status_code in (200, 201), question.text
    question = question.json()
    assert question["question_type"] == "SINGLE_CHOICE"
    return exam, question


def _option_id(question, *, correct):
    return next(
        opt["id"] for opt in question["options"] if opt["is_correct"] is correct
    )


def _submit(client, student, exam, question, option_id):
    assert (
        client.get(
            f"/student/exams/{exam['id']}/start", headers=student["headers"]
        ).status_code
        == 200
    )
    response = client.post(
        f"/student/exams/{exam['id']}/submit",
        json={
            "answers": [
                {
                    "question_id": question["id"],
                    "answer_data": {"selected_option_id": option_id},
                }
            ]
        },
        headers=student["headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
def test_a_correct_single_choice_answer_is_scored(client, db, test_student):
    """The regression: this used to score 0 for a correct answer."""
    teacher = create_teacher(client, db)
    exam, question = _single_choice_exam(client, teacher, points=10)

    result = _submit(
        client, test_student, exam, question, _option_id(question, correct=True)
    )

    assert result["total_score"] == 10.0
    assert result["max_score"] == 10.0


@pytest.mark.integration
def test_a_wrong_single_choice_answer_scores_zero(client, db, test_student):
    teacher = create_teacher(client, db)
    exam, question = _single_choice_exam(client, teacher, points=10)

    result = _submit(
        client, test_student, exam, question, _option_id(question, correct=False)
    )

    assert result["total_score"] == 0.0
    assert result["max_score"] == 10.0
