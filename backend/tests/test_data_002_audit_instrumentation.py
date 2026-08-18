import uuid

import pytest
from sqlalchemy import select

from app.models.audit_event import AuditEvent
from app.models.exam import Exam
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from app.services.audit_service import AuditService
from tests.test_authorization_idor import create_exam, create_topic


def _events(db, request_id, action=None):
    db.expire_all()
    statement = select(AuditEvent).where(AuditEvent.request_id == request_id)
    if action is not None:
        statement = statement.where(AuditEvent.action == action)
    return db.scalars(statement).all()


# ---------------------------------------------------------------------------
# Success-path: one correctly-shaped event per newly wired action.
# ---------------------------------------------------------------------------


def test_topic_create_update_delete_emit_one_audit_event_each(
    client, db, test_teacher
):
    create_request_id = str(uuid.uuid4())
    created = client.post(
        "/topics",
        json={"name": f"Audited topic {uuid.uuid4()}"},
        headers={**test_teacher["headers"], "X-Request-ID": create_request_id},
    )
    assert created.status_code == 201
    topic_id = created.json()["id"]

    create_events = _events(db, create_request_id, "topic.create")
    assert len(create_events) == 1
    assert create_events[0].outcome == "success"
    assert create_events[0].entity_type == "topic"
    assert create_events[0].entity_id == topic_id
    assert create_events[0].owner_id == test_teacher["id"]
    assert create_events[0].changes == {}

    update_request_id = str(uuid.uuid4())
    updated = client.put(
        f"/topics/{topic_id}",
        json={"name": "Renamed topic"},
        headers={**test_teacher["headers"], "X-Request-ID": update_request_id},
    )
    assert updated.status_code == 200
    update_events = _events(db, update_request_id, "topic.update")
    assert len(update_events) == 1
    assert update_events[0].entity_id == topic_id

    delete_request_id = str(uuid.uuid4())
    deleted = client.delete(
        f"/topics/{topic_id}",
        headers={**test_teacher["headers"], "X-Request-ID": delete_request_id},
    )
    assert deleted.status_code == 200
    delete_events = _events(db, delete_request_id, "topic.delete")
    assert len(delete_events) == 1
    assert delete_events[0].entity_id == topic_id


def test_exam_create_update_delete_emit_one_audit_event_each(
    client, db, test_teacher
):
    create_request_id = str(uuid.uuid4())
    created = client.post(
        "/exams",
        json={
            "title": f"Audited exam {uuid.uuid4()}",
            "duration_minutes": 30,
            "is_published": False,
        },
        headers={**test_teacher["headers"], "X-Request-ID": create_request_id},
    )
    assert created.status_code == 200
    exam = created.json()
    exam_id = exam["id"]

    create_events = _events(db, create_request_id, "exam.create")
    assert len(create_events) == 1
    assert create_events[0].entity_id == exam_id
    assert create_events[0].owner_id == test_teacher["id"]

    update_request_id = str(uuid.uuid4())
    updated = client.put(
        f"/exams/{exam_id}",
        json={
            "title": "Renamed exam",
            "duration_minutes": 45,
            "is_published": False,
        },
        headers={**test_teacher["headers"], "X-Request-ID": update_request_id},
    )
    assert updated.status_code == 200
    update_events = _events(db, update_request_id, "exam.update")
    assert len(update_events) == 1
    assert update_events[0].entity_id == exam_id

    delete_request_id = str(uuid.uuid4())
    deleted = client.delete(
        f"/exams/{exam_id}",
        headers={**test_teacher["headers"], "X-Request-ID": delete_request_id},
    )
    assert deleted.status_code == 200
    delete_events = _events(db, delete_request_id, "exam.delete")
    assert len(delete_events) == 1
    assert delete_events[0].entity_id == exam_id


def test_exam_publish_and_unpublish_emit_dedicated_audit_events(
    client, db, test_teacher
):
    created = client.post(
        "/exams",
        json={
            "title": f"Publish exam {uuid.uuid4()}",
            "duration_minutes": 30,
            "is_published": False,
        },
        headers=test_teacher["headers"],
    )
    assert created.status_code == 200
    exam = created.json()
    exam_id = exam["id"]

    publish_request_id = str(uuid.uuid4())
    published = client.put(
        f"/exams/{exam_id}",
        json={"title": exam["title"], "duration_minutes": 30, "is_published": True},
        headers={**test_teacher["headers"], "X-Request-ID": publish_request_id},
    )
    assert published.status_code == 200
    publish_events = _events(db, publish_request_id, "exam.publish")
    assert len(publish_events) == 1
    assert publish_events[0].changes == {
        "is_published": {"before": False, "after": True}
    }
    assert publish_events[0].owner_id == test_teacher["id"]
    # No generic exam.update event should also fire for a publish toggle.
    assert _events(db, publish_request_id, "exam.update") == []

    unpublish_request_id = str(uuid.uuid4())
    unpublished = client.put(
        f"/exams/{exam_id}",
        json={"title": exam["title"], "duration_minutes": 30, "is_published": False},
        headers={**test_teacher["headers"], "X-Request-ID": unpublish_request_id},
    )
    assert unpublished.status_code == 200
    unpublish_events = _events(db, unpublish_request_id, "exam.unpublish")
    assert len(unpublish_events) == 1
    assert unpublish_events[0].changes == {
        "is_published": {"before": True, "after": False}
    }


def test_question_create_via_bank_and_via_exam_emit_audit_events(
    client, db, test_teacher
):
    bank_request_id = str(uuid.uuid4())
    bank_question = client.post(
        "/questions",
        json={
            "content": f"Bank question {uuid.uuid4()}",
            "points": 1,
            "options": [
                {"content": "A", "is_correct": True},
                {"content": "B", "is_correct": False},
            ],
        },
        headers={**test_teacher["headers"], "X-Request-ID": bank_request_id},
    )
    assert bank_question.status_code == 201
    bank_question_id = bank_question.json()["id"]
    bank_events = _events(db, bank_request_id, "question.create")
    assert len(bank_events) == 1
    assert bank_events[0].entity_id == bank_question_id
    assert bank_events[0].owner_id == test_teacher["id"]

    exam = create_exam(client, test_teacher, f"Question host exam {uuid.uuid4()}")
    exam_question_request_id = str(uuid.uuid4())
    exam_question = client.post(
        f"/exams/{exam['id']}/questions",
        json={
            "content": f"Exam question {uuid.uuid4()}",
            "points": 2,
            "options": [
                {"content": "A", "is_correct": True},
                {"content": "B", "is_correct": False},
            ],
        },
        headers={
            **test_teacher["headers"],
            "X-Request-ID": exam_question_request_id,
        },
    )
    assert exam_question.status_code == 200
    exam_question_id = exam_question.json()["id"]
    exam_events = _events(db, exam_question_request_id, "question.create")
    assert len(exam_events) == 1
    assert exam_events[0].entity_id == exam_question_id
    assert exam_events[0].owner_id == test_teacher["id"]
    # No admin.override should fire for the owning teacher's own exam.
    assert _events(db, exam_question_request_id, "admin.override") == []

    update_request_id = str(uuid.uuid4())
    updated = client.put(
        f"/questions/{bank_question_id}",
        json={"content": "Updated content"},
        headers={**test_teacher["headers"], "X-Request-ID": update_request_id},
    )
    assert updated.status_code == 200
    assert len(_events(db, update_request_id, "question.update")) == 1

    delete_request_id = str(uuid.uuid4())
    deleted = client.delete(
        f"/questions/{bank_question_id}",
        headers={**test_teacher["headers"], "X-Request-ID": delete_request_id},
    )
    assert deleted.status_code == 200
    assert len(_events(db, delete_request_id, "question.delete")) == 1


def test_material_upload_and_delete_emit_audit_events_with_safe_metadata(
    client, db, test_teacher
):
    upload_request_id = str(uuid.uuid4())
    files = {"file": ("audited-lesson.txt", b"Lesson content", "text/plain")}
    uploaded = client.post(
        "/materials/upload",
        files=files,
        headers={**test_teacher["headers"], "X-Request-ID": upload_request_id},
    )
    assert uploaded.status_code == 200
    material_id = uploaded.json()["id"]

    upload_events = _events(db, upload_request_id, "material.upload")
    assert len(upload_events) == 1
    event = upload_events[0]
    assert event.entity_type == "study_material"
    assert event.entity_id == material_id
    assert event.owner_id == test_teacher["id"]
    assert event.event_metadata == {"file_type": "txt"}
    # No raw filename/path leaks into the audited payload.
    assert "audited-lesson" not in str(event.event_metadata)
    assert "path" not in event.event_metadata

    delete_request_id = str(uuid.uuid4())
    deleted = client.delete(
        f"/materials/{material_id}?cascade=true",
        headers={**test_teacher["headers"], "X-Request-ID": delete_request_id},
    )
    assert deleted.status_code == 200
    delete_events = _events(db, delete_request_id, "material.delete")
    assert len(delete_events) == 1
    assert delete_events[0].event_metadata == {"cascade": True}


def test_flashcard_deck_and_card_create_emit_audit_events(
    client, db, test_teacher
):
    topic = create_topic(client, test_teacher, f"Flashcard topic {uuid.uuid4()}")

    deck_request_id = str(uuid.uuid4())
    deck = client.post(
        "/flashcards/decks",
        json={"topic_id": topic["id"], "title": "Deck", "description": "d"},
        headers={**test_teacher["headers"], "X-Request-ID": deck_request_id},
    )
    assert deck.status_code == 200
    deck_id = deck.json()["id"]
    deck_events = _events(db, deck_request_id, "flashcard_deck.create")
    assert len(deck_events) == 1
    assert deck_events[0].entity_id == deck_id
    assert deck_events[0].owner_id == test_teacher["id"]

    card_request_id = str(uuid.uuid4())
    card = client.post(
        f"/flashcards/decks/{deck_id}/cards",
        json={
            "deck_id": deck_id,
            "front_content": "Front",
            "back_content": "Back",
            "order_index": 0,
        },
        headers={**test_teacher["headers"], "X-Request-ID": card_request_id},
    )
    assert card.status_code == 200
    card_id = card.json()["id"]
    card_events = _events(db, card_request_id, "flashcard.create")
    assert len(card_events) == 1
    assert card_events[0].entity_id == card_id
    assert card_events[0].owner_id == test_teacher["id"]


def test_submission_graded_emits_audit_event(client, db, sample_exam, test_student):
    exam_id = sample_exam["exam"]["id"]
    questions = sample_exam["questions"]

    start = client.get(
        f"/student/exams/{exam_id}/start", headers=test_student["headers"]
    )
    assert start.status_code == 200

    submit_request_id = str(uuid.uuid4())
    submitted = client.post(
        f"/student/exams/{exam_id}/submit",
        json={
            "answers": [
                {
                    "question_id": questions[0]["id"],
                    "selected_option_id": next(
                        opt["id"]
                        for opt in questions[0]["options"]
                        if opt["is_correct"]
                    ),
                }
            ]
        },
        headers={**test_student["headers"], "X-Request-ID": submit_request_id},
    )
    assert submitted.status_code == 200
    submission_id = submitted.json()["submission_id"]

    events = _events(db, submit_request_id, "submission.graded")
    assert len(events) == 1
    event = events[0]
    assert event.entity_type == "submission"
    assert event.entity_id == submission_id
    assert event.owner_id == uuid.UUID(str(test_student["id"]))
    assert event.actor_role == "student"
    assert event.changes["total_score"]["before"] == 0.0
    assert event.changes["total_score"]["after"] == submitted.json()["total_score"]
    assert event.event_metadata["max_score"] == submitted.json()["max_score"]


def test_user_registration_emits_user_create_event_with_system_actor(client, db):
    request_id = str(uuid.uuid4())
    email = f"audited_register_{uuid.uuid4()}@example.com"
    registered = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Audited Registrant",
            "role": "student",
            "password": "testpassword",
        },
        headers={"X-Request-ID": request_id},
    )
    assert registered.status_code == 200
    user_id = registered.json()["id"]

    events = _events(db, request_id, "user.create")
    assert len(events) == 1
    event = events[0]
    assert event.entity_id == user_id
    assert event.actor_type == "system"
    assert event.actor_id is None
    assert event.actor_role == "system"
    assert event.owner_id is None
    assert event.changes == {"role": {"before": None, "after": "student"}}


def test_admin_role_change_and_disable_emit_audit_events(
    client, db, test_admin, test_student
):
    role_request_id = str(uuid.uuid4())
    role_changed = client.put(
        f"/admin/users/{test_student['id']}/role?new_role=teacher",
        headers={**test_admin["headers"], "X-Request-ID": role_request_id},
    )
    assert role_changed.status_code == 200
    role_events = _events(db, role_request_id, "user.role_change")
    assert len(role_events) == 1
    assert role_events[0].entity_id == str(test_student["id"])
    assert role_events[0].owner_id is None
    assert role_events[0].changes == {
        "role": {"before": "student", "after": "teacher"}
    }

    email = f"disable_target_{uuid.uuid4()}@example.com"
    registered = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Disable Target",
            "role": "student",
            "password": "testpassword",
        },
    )
    assert registered.status_code == 200
    target_id = registered.json()["id"]

    disable_request_id = str(uuid.uuid4())
    disabled = client.delete(
        f"/admin/users/{target_id}",
        headers={**test_admin["headers"], "X-Request-ID": disable_request_id},
    )
    assert disabled.status_code == 200
    disable_events = _events(db, disable_request_id, "user.disable")
    assert len(disable_events) == 1
    assert disable_events[0].entity_id == target_id
    assert disable_events[0].actor_role == "admin"


# ---------------------------------------------------------------------------
# Atomicity: an audit-write failure must roll back the business mutation too,
# leaving no partial/false-success state and no audit row for that request.
# ---------------------------------------------------------------------------


def test_topic_create_audit_failure_rolls_back_mutation(
    client, db, test_teacher, monkeypatch
):
    request_id = str(uuid.uuid4())
    unique_name = f"Atomic topic {uuid.uuid4()}"

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("canary-topic-create-audit-failure")

    monkeypatch.setattr(AuditService, "record", fail_audit)
    with pytest.raises(RuntimeError, match="canary-topic-create-audit-failure"):
        client.post(
            "/topics",
            json={"name": unique_name},
            headers={**test_teacher["headers"], "X-Request-ID": request_id},
        )
    monkeypatch.undo()

    db.expire_all()
    assert (
        db.scalar(
            select(AuditEvent.event_id).where(AuditEvent.request_id == request_id)
        )
        is None
    )
    # The failed create must not have left a partially-persisted topic.
    assert db.scalar(select(Topic.id).where(Topic.name == unique_name)) is None


def test_exam_publish_audit_failure_rolls_back_mutation(
    client, db, test_teacher, monkeypatch
):
    original_title = f"Atomic publish exam {uuid.uuid4()}"
    created = client.post(
        "/exams",
        json={
            "title": original_title,
            "duration_minutes": 30,
            "is_published": False,
        },
        headers=test_teacher["headers"],
    )
    exam_id = created.json()["id"]
    request_id = str(uuid.uuid4())

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("canary-exam-publish-audit-failure")

    monkeypatch.setattr(AuditService, "record", fail_audit)
    with pytest.raises(RuntimeError, match="canary-exam-publish-audit-failure"):
        client.put(
            f"/exams/{exam_id}",
            json={
                "title": "Should not persist",
                "duration_minutes": 30,
                "is_published": True,
            },
            headers={**test_teacher["headers"], "X-Request-ID": request_id},
        )
    monkeypatch.undo()

    db.expire_all()
    exam = db.get(Exam, uuid.UUID(exam_id))
    assert exam.is_published is False
    assert exam.title == original_title
    assert (
        db.scalar(
            select(AuditEvent.event_id).where(AuditEvent.request_id == request_id)
        )
        is None
    )


def test_material_upload_audit_failure_rolls_back_row_and_deletes_stored_file(
    client, db, test_teacher, monkeypatch
):
    request_id = str(uuid.uuid4())

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("canary-material-upload-audit-failure")

    monkeypatch.setattr(AuditService, "record", fail_audit)
    files = {"file": ("atomic-upload.txt", b"content", "text/plain")}
    with pytest.raises(RuntimeError, match="canary-material-upload-audit-failure"):
        client.post(
            "/materials/upload",
            files=files,
            headers={**test_teacher["headers"], "X-Request-ID": request_id},
        )
    monkeypatch.undo()

    db.expire_all()
    assert (
        db.scalar(
            select(StudyMaterial.id).where(
                StudyMaterial.title == "atomic-upload.txt"
            )
        )
        is None
    )
    assert (
        db.scalar(
            select(AuditEvent.event_id).where(AuditEvent.request_id == request_id)
        )
        is None
    )


def test_user_role_change_audit_failure_rolls_back_mutation(
    client, db, test_admin, test_student, monkeypatch
):
    request_id = str(uuid.uuid4())

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("canary-role-change-audit-failure")

    monkeypatch.setattr(AuditService, "record", fail_audit)
    with pytest.raises(RuntimeError, match="canary-role-change-audit-failure"):
        client.put(
            f"/admin/users/{test_student['id']}/role?new_role=teacher",
            headers={**test_admin["headers"], "X-Request-ID": request_id},
        )
    monkeypatch.undo()

    db.expire_all()
    user = db.get(User, uuid.UUID(str(test_student["id"])))
    assert user.role == "student"
    assert (
        db.scalar(
            select(AuditEvent.event_id).where(AuditEvent.request_id == request_id)
        )
        is None
    )
