import uuid

from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from tests.test_authorization_idor import (
    create_exam,
    create_question,
    create_teacher,
    create_topic,
)


def assert_conflict(response, error_code: str) -> None:
    assert response.status_code == 409
    assert response.json()["error_code"] == error_code


def test_exam_question_mutations_are_blocked_after_submission(
    client,
    db,
    sample_exam,
    test_student,
):
    exam = sample_exam["exam"]
    question = sample_exam["questions"][0]
    started = client.get(
        f"/student/exams/{exam['id']}/start",
        headers=test_student["headers"],
    )
    assert started.status_code == 200

    readable = client.get(
        f"/questions/{question['id']}",
        headers=sample_exam["teacher"]["headers"],
    )
    assert readable.status_code == 200

    update_question = client.put(
        f"/questions/{question['id']}",
        json={"content": "Must remain immutable"},
        headers=sample_exam["teacher"]["headers"],
    )
    assert_conflict(
        update_question,
        "QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS",
    )

    delete_question = client.delete(
        f"/questions/{question['id']}",
        headers=sample_exam["teacher"]["headers"],
    )
    assert_conflict(
        delete_question,
        "QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS",
    )

    create_child = client.post(
        f"/exams/{exam['id']}/questions",
        json={
            "content": "Late question",
            "points": 1,
            "options": [
                {"content": "A", "is_correct": True},
                {"content": "B", "is_correct": False},
            ],
        },
        headers=sample_exam["teacher"]["headers"],
    )
    assert_conflict(
        create_child,
        "EXAM_QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS",
    )

    standalone = create_question(
        client,
        sample_exam["teacher"],
        f"Standalone retained guard {uuid.uuid4()}",
    )
    bulk_assign = client.post(
        f"/exams/{exam['id']}/questions/bulk",
        json={"question_ids": [standalone["id"]]},
        headers=sample_exam["teacher"]["headers"],
    )
    assert_conflict(
        bulk_assign,
        "EXAM_QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS",
    )

    update_exam = client.put(
        f"/exams/{exam['id']}",
        json={
            "title": "Must remain immutable",
            "description": exam.get("description"),
            "duration_minutes": exam["duration_minutes"],
            "is_published": exam["is_published"],
            "topic_id": exam.get("topic_id"),
        },
        headers=sample_exam["teacher"]["headers"],
    )
    assert_conflict(
        update_exam,
        "EXAM_QUESTION_MUTATION_BLOCKED_BY_RETAINED_RECORDS",
    )

    delete_exam = client.delete(
        f"/exams/{exam['id']}",
        headers=sample_exam["teacher"]["headers"],
    )
    assert_conflict(
        delete_exam,
        "EXAM_DELETE_BLOCKED_BY_RETAINED_RECORDS",
    )
    db.rollback()

def test_user_topic_and_material_destructive_guards(
    client,
    db,
    test_admin,
    test_student,
):
    owner = create_teacher(client, db)
    topic_data = create_topic(
        client,
        owner,
        f"Retained topic {uuid.uuid4()}",
    )
    create_exam(
        client,
        owner,
        f"Linked exam {uuid.uuid4()}",
        topic_id=topic_data["id"],
    )

    demotion = client.put(
        f"/admin/users/{owner['id']}/role?new_role=student",
        headers=test_admin["headers"],
    )
    assert_conflict(demotion, "USER_ROLE_CHANGE_BLOCKED_BY_OWNED_DATA")

    user_delete = client.delete(
        f"/admin/users/{owner['id']}",
        headers=test_admin["headers"],
    )
    assert_conflict(user_delete, "USER_DELETE_BLOCKED_BY_RETAINED_DATA")

    topic_delete = client.delete(
        f"/topics/{topic_data['id']}",
        headers=owner["headers"],
    )
    assert_conflict(topic_delete, "TOPIC_DELETE_BLOCKED_BY_LINKED_RECORDS")

    material_topic = Topic(
        owner_id=owner["id"],
        name=f"Material topic {uuid.uuid4()}",
    )
    material = StudyMaterial(
        uploader_id=owner["id"],
        title="retained.txt",
        file_type="txt",
        file_path="uploads/materials/retained-does-not-exist.txt",
        ai_status="completed",
    )
    db.add_all([material_topic, material])
    db.flush()
    deck = FlashcardDeck(
        topic_id=material_topic.id,
        material_id=material.id,
        title="Retained deck",
    )
    db.add(deck)
    db.flush()
    card = Flashcard(
        deck_id=deck.id,
        front_content="Front",
        back_content="Back",
    )
    db.add(card)
    db.flush()
    progress = FlashcardProgress(
        student_id=uuid.UUID(test_student["id"]),
        flashcard_id=card.id,
    )
    db.add(progress)
    db.commit()

    material_delete = client.delete(
        f"/materials/{material.id}?cascade=true",
        headers=owner["headers"],
    )
    assert_conflict(
        material_delete,
        "MATERIAL_CASCADE_BLOCKED_BY_RETAINED_RECORDS",
    )

    material_id = material.id
    deck_id = deck.id
    progress_id = progress.id
    db.rollback()
    db.expire_all()
    assert db.get(StudyMaterial, material_id) is not None
    assert db.get(FlashcardDeck, deck_id) is not None
    assert db.get(FlashcardProgress, progress_id) is not None
    assert db.get(User, owner["id"]).role == "teacher"
