import uuid

from sqlalchemy import select

from app.models.exam import Question

from tests.test_authorization_idor import create_exam, create_question


def test_question_list_and_bulk_authorization_have_bounded_queries(
    client,
    db,
    test_teacher,
    assert_num_queries,
):
    exam = create_exam(client, test_teacher, f"Budget exam {uuid.uuid4()}")
    questions = [
        create_question(
            client,
            test_teacher,
            f"Budget question {index} {uuid.uuid4()}",
        )
        for index in range(50)
    ]

    with assert_num_queries(5):
        response = client.get(
            "/questions?page=1&size=50",
            headers=test_teacher["headers"],
        )
    assert response.status_code == 200

    with assert_num_queries(7):
        response = client.post(
            f"/exams/{exam['id']}/questions/bulk",
            json={"question_ids": [question["id"] for question in questions]},
            headers=test_teacher["headers"],
        )
    assert response.status_code == 200
    assert response.json()["message"] == "Added 50 questions to exam"

    db.expire_all()
    question_ids = [uuid.UUID(question["id"]) for question in questions]
    persisted = db.scalars(
        select(Question).where(Question.id.in_(question_ids))
    ).all()
    assert len(persisted) == 50
    assert all(str(question.exam_id) == exam["id"] for question in persisted)
