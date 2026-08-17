import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models.exam import Exam, Question
from app.models.material import StudyMaterial
from app.models.submission import Submission
from app.models.topic import Topic
from tests.test_authorization_idor import (
    create_exam,
    create_question,
    create_teacher,
    create_topic,
)


def test_history_and_analytics_are_owner_scoped(
    client,
    db,
    test_teacher,
    test_admin,
    test_student,
):
    other_teacher = create_teacher(client, db)
    owner_topic = Topic(
        owner_id=test_teacher["id"],
        name=f"Owner analytics {uuid.uuid4()}",
    )
    foreign_topic = Topic(
        owner_id=other_teacher["id"],
        name=f"Foreign analytics {uuid.uuid4()}",
    )
    db.add_all([owner_topic, foreign_topic])
    db.flush()
    owner_exam = Exam(
        creator_id=test_teacher["id"],
        topic_id=owner_topic.id,
        title="Owner analytics exam",
        duration_minutes=30,
        is_published=True,
    )
    foreign_exam = Exam(
        creator_id=other_teacher["id"],
        topic_id=foreign_topic.id,
        title="Foreign analytics exam",
        duration_minutes=30,
        is_published=True,
    )
    db.add_all([owner_exam, foreign_exam])
    db.flush()
    owner_submission = Submission(
        exam_id=owner_exam.id,
        student_id=uuid.UUID(test_student["id"]),
        status="submitted",
        total_score=80,
        end_time=datetime.now(timezone.utc),
    )
    foreign_submission = Submission(
        exam_id=foreign_exam.id,
        student_id=uuid.UUID(test_student["id"]),
        status="submitted",
        total_score=20,
        end_time=datetime.now(timezone.utc),
    )
    db.add_all([owner_submission, foreign_submission])
    db.commit()

    history = client.get(
        "/history/submissions",
        headers=test_teacher["headers"],
    )
    assert history.status_code == 200
    history_ids = {item["id"] for item in history.json()["items"]}
    assert str(owner_submission.id) in history_ids
    assert str(foreign_submission.id) not in history_ids

    request_id = str(uuid.uuid4())
    detail_headers = {
        **test_teacher["headers"],
        "X-Request-ID": request_id,
    }
    foreign_detail = client.get(
        f"/history/submissions/{foreign_submission.id}",
        headers=detail_headers,
    )
    missing_detail = client.get(
        f"/history/submissions/{uuid.uuid4()}",
        headers=detail_headers,
    )
    assert foreign_detail.status_code == missing_detail.status_code == 404
    assert foreign_detail.json() == missing_detail.json()
    assert foreign_detail.json()["error_code"] == "SUBMISSION_NOT_FOUND"

    admin_history = client.get(
        "/history/submissions",
        headers=test_admin["headers"],
    )
    admin_ids = {item["id"] for item in admin_history.json()["items"]}
    assert {str(owner_submission.id), str(foreign_submission.id)} <= admin_ids

    overview = client.get(
        "/analytics/overview",
        headers=test_teacher["headers"],
    )
    assert overview.status_code == 200
    assert overview.json()["total_exams"] == 1
    assert overview.json()["total_submissions"] == 1
    assert overview.json()["total_students"] == 1

    foreign_stats = client.get(
        f"/analytics/score-stats?exam_id={foreign_exam.id}",
        headers=test_teacher["headers"],
    )
    missing_stats = client.get(
        f"/analytics/score-stats?exam_id={uuid.uuid4()}",
        headers=test_teacher["headers"],
    )
    assert foreign_stats.status_code == missing_stats.status_code == 200
    assert foreign_stats.json() == missing_stats.json()
    assert foreign_stats.json()["highest_score"] == 0


def test_flashcard_management_and_learning_visibility_matrix(
    client,
    db,
    test_teacher,
    test_admin,
    test_student,
):
    other_teacher = create_teacher(client, db)
    topic = create_topic(
        client,
        test_teacher,
        f"Flashcard owner {uuid.uuid4()}",
    )
    deck_response = client.post(
        "/flashcards/decks",
        json={
            "title": "Owner deck",
            "description": "Derived ownership",
            "topic_id": topic["id"],
        },
        headers=test_teacher["headers"],
    )
    assert deck_response.status_code == 200
    deck = deck_response.json()
    card_response = client.post(
        f"/flashcards/decks/{deck['id']}/cards",
        json={
            "deck_id": deck["id"],
            "front_content": "Front",
            "back_content": "Back",
            "order_index": 0,
        },
        headers=test_teacher["headers"],
    )
    assert card_response.status_code == 200

    assert (
        client.get(
            f"/flashcards/decks/{deck['id']}",
            headers=test_teacher["headers"],
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/flashcards/decks/{deck['id']}",
            headers=other_teacher["headers"],
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/flashcards/decks/{deck['id']}",
            headers=test_admin["headers"],
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/flashcards/decks/{deck['id']}",
            headers=test_student["headers"],
        ).status_code
        == 200
    )
    study = client.get(
        f"/flashcards/student/decks/{deck['id']}/study",
        headers=test_student["headers"],
    )
    assert study.status_code == 200
    assert [card["id"] for card in study.json()] == [card_response.json()["id"]]

    denied_card = client.post(
        f"/flashcards/decks/{deck['id']}/cards",
        json={
            "deck_id": deck["id"],
            "front_content": "Denied",
            "back_content": "Denied",
            "order_index": 1,
        },
        headers=other_teacher["headers"],
    )
    assert denied_card.status_code == 404
    assert denied_card.json()["error_code"] == "DECK_NOT_FOUND"


def test_material_and_question_lists_do_not_cross_owner_boundary(
    client,
    db,
    test_teacher,
):
    other_teacher = create_teacher(client, db)
    owner_question = create_question(
        client,
        test_teacher,
        f"Owner list question {uuid.uuid4()}",
    )
    foreign_question = create_question(
        client,
        other_teacher,
        f"Foreign list question {uuid.uuid4()}",
    )
    owner_material = StudyMaterial(
        uploader_id=test_teacher["id"],
        title="owner-list.txt",
        file_type="txt",
        file_path="uploads/materials/owner-list.txt",
        ai_status="pending",
    )
    foreign_material = StudyMaterial(
        uploader_id=other_teacher["id"],
        title="foreign-list.txt",
        file_type="txt",
        file_path="uploads/materials/foreign-list.txt",
        ai_status="pending",
    )
    db.add_all([owner_material, foreign_material])
    db.commit()

    question_items = client.get(
        "/questions?page=1&size=100",
        headers=test_teacher["headers"],
    ).json()["items"]
    question_ids = {item["id"] for item in question_items}
    assert owner_question["id"] in question_ids
    assert foreign_question["id"] not in question_ids

    material_items = client.get(
        "/materials?page=1&size=100",
        headers=test_teacher["headers"],
    ).json()["items"]
    material_ids = {item["id"] for item in material_items}
    assert str(owner_material.id) in material_ids
    assert str(foreign_material.id) not in material_ids
    assert all("file_path" not in item for item in material_items)


def test_cross_resource_links_require_one_owner_and_leave_no_partial_write(
    client,
    db,
    test_teacher,
):
    other_teacher = create_teacher(client, db)
    owner_topic = create_topic(
        client,
        test_teacher,
        f"Owner link topic {uuid.uuid4()}",
    )
    foreign_topic = create_topic(
        client,
        other_teacher,
        f"Foreign link topic {uuid.uuid4()}",
    )
    material = StudyMaterial(
        uploader_id=test_teacher["id"],
        topic_id=uuid.UUID(owner_topic["id"]),
        title="owner-link.txt",
        file_type="txt",
        file_path="uploads/materials/owner-link.txt",
        ai_status="completed",
    )
    db.add(material)
    db.commit()

    initial_topics = db.scalar(select(func.count(Topic.id)))
    initial_exams = db.scalar(select(func.count(Exam.id)))
    initial_questions = db.scalar(select(func.count(Question.id)))
    initial_materials = db.scalar(select(func.count(StudyMaterial.id)))

    foreign_parent = client.post(
        "/topics",
        json={
            "name": "Invalid child",
            "parent_id": foreign_topic["id"],
        },
        headers=test_teacher["headers"],
    )
    assert foreign_parent.status_code == 404
    assert foreign_parent.json()["error_code"] == "TOPIC_NOT_FOUND"

    foreign_exam_topic = client.post(
        "/exams",
        json={
            "title": "Invalid exam",
            "duration_minutes": 30,
            "topic_id": foreign_topic["id"],
        },
        headers=test_teacher["headers"],
    )
    assert foreign_exam_topic.status_code == 404
    assert foreign_exam_topic.json()["error_code"] == "TOPIC_NOT_FOUND"

    foreign_question_topic = client.post(
        "/questions",
        json={
            "content": "Invalid question",
            "topic_id": foreign_topic["id"],
            "options": [],
        },
        headers=test_teacher["headers"],
    )
    assert foreign_question_topic.status_code == 404
    assert foreign_question_topic.json()["error_code"] == "TOPIC_NOT_FOUND"

    foreign_material_topic = client.post(
        "/materials/upload",
        data={"topic_id": foreign_topic["id"]},
        files={"file": ("forbidden.txt", b"private", "text/plain")},
        headers=test_teacher["headers"],
    )
    assert foreign_material_topic.status_code == 404
    assert foreign_material_topic.json()["error_code"] == "TOPIC_NOT_FOUND"

    mismatched_topic_kit = client.post(
        "/flashcards/ai/generate-topic-kit",
        json={
            "material_id": str(material.id),
            "topic_id": foreign_topic["id"],
        },
        headers=test_teacher["headers"],
    )
    assert mismatched_topic_kit.status_code == 404
    assert mismatched_topic_kit.json()["error_code"] == "TOPIC_NOT_FOUND"

    db.rollback()
    assert db.scalar(select(func.count(Topic.id))) == initial_topics
    assert db.scalar(select(func.count(Exam.id))) == initial_exams
    assert db.scalar(select(func.count(Question.id))) == initial_questions
    assert db.scalar(select(func.count(StudyMaterial.id))) == initial_materials
