import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.db.soft_delete import RESTORE_WINDOW
from app.models.audit_event import AuditEvent
from app.models.exam import Exam, Question
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from tests.test_authorization_idor import (
    create_exam,
    create_question,
    create_teacher,
    create_topic,
)


def _create_material(client, db, owner):
    material = StudyMaterial(
        uploader_id=owner["id"],
        title=f"Restore material {uuid.uuid4()}.txt",
        file_type="txt",
        file_path=f"uploads/materials/restore-probe-{uuid.uuid4()}.txt",
        ai_status="completed",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return {"id": str(material.id)}


class RestoreCase:
    def __init__(self, name, path, model, not_found_code, expired_code, create):
        self.name = name
        self.path = path
        self.model = model
        self.not_found_code = not_found_code
        self.expired_code = expired_code
        self.create = create


RESTORE_CASES = [
    RestoreCase(
        "topic",
        "/topics",
        Topic,
        "TOPIC_NOT_FOUND",
        "TOPIC_RESTORE_WINDOW_EXPIRED",
        lambda client, db, owner: create_topic(
            client, owner, f"Restore topic {uuid.uuid4()}"
        ),
    ),
    RestoreCase(
        "exam",
        "/exams",
        Exam,
        "EXAM_NOT_FOUND",
        "EXAM_RESTORE_WINDOW_EXPIRED",
        lambda client, db, owner: create_exam(
            client, owner, f"Restore exam {uuid.uuid4()}"
        ),
    ),
    RestoreCase(
        "question",
        "/questions",
        Question,
        "QUESTION_NOT_FOUND",
        "QUESTION_RESTORE_WINDOW_EXPIRED",
        lambda client, db, owner: create_question(
            client, owner, f"Restore question {uuid.uuid4()}"
        ),
    ),
    RestoreCase(
        "material",
        "/materials",
        StudyMaterial,
        "MATERIAL_NOT_FOUND",
        "MATERIAL_RESTORE_WINDOW_EXPIRED",
        _create_material,
    ),
]


def _set_deleted_at(db, model, resource_id, deleted_at):
    db.execute(
        update(model)
        .where(model.id == uuid.UUID(str(resource_id)))
        .values(deleted_at=deleted_at)
    )
    db.commit()


def _get_including_deleted(db, model, resource_id):
    db.expire_all()
    return db.scalar(
        select(model)
        .where(model.id == uuid.UUID(str(resource_id)))
        .execution_options(include_deleted=True)
    )


@pytest.mark.parametrize("case", RESTORE_CASES, ids=lambda c: c.name)
def test_admin_and_owner_restore_within_window(client, db, test_admin, case):
    owner = create_teacher(client, db)
    resource = case.create(client, db, owner)
    resource_id = resource["id"]

    assert (
        client.delete(f"{case.path}/{resource_id}", headers=owner["headers"]).status_code
        == 200
    )

    # Owning teacher restores their own soft-deleted record.
    owner_restore = client.post(
        f"{case.path}/{resource_id}/restore", headers=owner["headers"]
    )
    assert owner_restore.status_code == 200
    restored = _get_including_deleted(db, case.model, resource_id)
    assert restored.deleted_at is None
    assert restored.deleted_by_id is None

    # Soft-delete again and let admin restore it via override.
    assert (
        client.delete(f"{case.path}/{resource_id}", headers=owner["headers"]).status_code
        == 200
    )
    admin_restore = client.post(
        f"{case.path}/{resource_id}/restore", headers=test_admin["headers"]
    )
    assert admin_restore.status_code == 200
    restored_by_admin = _get_including_deleted(db, case.model, resource_id)
    assert restored_by_admin.deleted_at is None
    assert restored_by_admin.deleted_by_id is None


@pytest.mark.parametrize("case", RESTORE_CASES, ids=lambda c: c.name)
def test_non_owner_teacher_student_and_anonymous_are_denied(
    client, db, test_student, case
):
    owner = create_teacher(client, db)
    other_teacher = create_teacher(client, db)
    resource = case.create(client, db, owner)
    resource_id = resource["id"]

    assert (
        client.delete(f"{case.path}/{resource_id}", headers=owner["headers"]).status_code
        == 200
    )

    anonymous_response = client.post(f"{case.path}/{resource_id}/restore")
    assert anonymous_response.status_code == 401

    student_response = client.post(
        f"{case.path}/{resource_id}/restore", headers=test_student["headers"]
    )
    assert student_response.status_code == 403

    non_owner_response = client.post(
        f"{case.path}/{resource_id}/restore", headers=other_teacher["headers"]
    )
    assert non_owner_response.status_code == 404
    assert non_owner_response.json()["error_code"] == case.not_found_code

    still_deleted = _get_including_deleted(db, case.model, resource_id)
    assert still_deleted.deleted_at is not None


@pytest.mark.parametrize("case", RESTORE_CASES, ids=lambda c: c.name)
def test_restore_window_exact_boundary(client, db, case):
    owner = create_teacher(client, db)
    resource = case.create(client, db, owner)
    resource_id = resource["id"]

    assert (
        client.delete(f"{case.path}/{resource_id}", headers=owner["headers"]).status_code
        == 200
    )

    # 29 days 23 hours ago: still inside the window, restorable.
    still_eligible = (
        datetime.now(timezone.utc) - RESTORE_WINDOW + timedelta(hours=1)
    )
    _set_deleted_at(db, case.model, resource_id, still_eligible)
    eligible_response = client.post(
        f"{case.path}/{resource_id}/restore", headers=owner["headers"]
    )
    assert eligible_response.status_code == 200
    assert _get_including_deleted(db, case.model, resource_id).deleted_at is None

    # Re-delete and push it to (and past) the exact 30-day cutoff.
    assert (
        client.delete(f"{case.path}/{resource_id}", headers=owner["headers"]).status_code
        == 200
    )
    expired = datetime.now(timezone.utc) - RESTORE_WINDOW
    _set_deleted_at(db, case.model, resource_id, expired)
    expired_response = client.post(
        f"{case.path}/{resource_id}/restore", headers=owner["headers"]
    )
    assert expired_response.status_code == 409
    assert expired_response.json()["error_code"] == case.expired_code
    assert (
        _get_including_deleted(db, case.model, resource_id).deleted_at is not None
    )


@pytest.mark.parametrize("case", RESTORE_CASES, ids=lambda c: c.name)
def test_restore_active_or_missing_record_is_canonical_not_found(
    client, db, case
):
    owner = create_teacher(client, db)
    resource = case.create(client, db, owner)
    resource_id = resource["id"]

    active_response = client.post(
        f"{case.path}/{resource_id}/restore", headers=owner["headers"]
    )
    assert active_response.status_code == 404
    assert active_response.json()["error_code"] == case.not_found_code

    missing_response = client.post(
        f"{case.path}/{uuid.uuid4()}/restore", headers=owner["headers"]
    )
    assert missing_response.status_code == 404
    assert missing_response.json()["error_code"] == case.not_found_code


def test_successful_restore_emits_exactly_one_audit_event(client, db):
    owner = create_teacher(client, db)
    topic = create_topic(client, owner, f"Audited restore topic {uuid.uuid4()}")
    topic_id = topic["id"]
    assert (
        client.delete(f"/topics/{topic_id}", headers=owner["headers"]).status_code
        == 200
    )

    request_id = str(uuid.uuid4())
    restore_response = client.post(
        f"/topics/{topic_id}/restore",
        headers={**owner["headers"], "X-Request-ID": request_id},
    )
    assert restore_response.status_code == 200

    db.expire_all()
    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.request_id == request_id,
            AuditEvent.action == "restore.performed",
        )
    ).all()
    assert len(events) == 1
    event = events[0]
    assert event.outcome == "success"
    assert event.actor_id == owner["id"]
    assert event.actor_role == "teacher"
    assert event.entity_type == "topic"
    assert event.entity_id == str(topic_id)
    assert event.owner_id == owner["id"]
    assert event.changes["deleted_at"]["after"] is None
    assert event.changes["deleted_at"]["before"]


def test_denied_and_expired_restore_attempts_emit_no_audit_event(
    client, db, test_student
):
    owner = create_teacher(client, db)
    other_teacher = create_teacher(client, db)
    topic = create_topic(
        client, owner, f"Unaudited restore topic {uuid.uuid4()}"
    )
    topic_id = topic["id"]
    assert (
        client.delete(f"/topics/{topic_id}", headers=owner["headers"]).status_code
        == 200
    )

    denied_request_id = str(uuid.uuid4())
    denied_response = client.post(
        f"/topics/{topic_id}/restore",
        headers={**other_teacher["headers"], "X-Request-ID": denied_request_id},
    )
    assert denied_response.status_code == 404

    student_request_id = str(uuid.uuid4())
    student_response = client.post(
        f"/topics/{topic_id}/restore",
        headers={**test_student["headers"], "X-Request-ID": student_request_id},
    )
    assert student_response.status_code == 403

    expired = datetime.now(timezone.utc) - RESTORE_WINDOW
    _set_deleted_at(db, Topic, topic_id, expired)
    expired_request_id = str(uuid.uuid4())
    expired_response = client.post(
        f"/topics/{topic_id}/restore",
        headers={**owner["headers"], "X-Request-ID": expired_request_id},
    )
    assert expired_response.status_code == 409

    db.expire_all()
    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.request_id.in_(
                [denied_request_id, student_request_id, expired_request_id]
            ),
            AuditEvent.action == "restore.performed",
        )
    ).all()
    assert events == []


def test_admin_restores_user_within_window_teacher_denied(
    client, db, test_admin, test_teacher
):
    email = f"restore_student_{uuid.uuid4()}@example.com"
    register = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Restore Student",
            "role": "student",
            "password": "testpassword",
        },
    )
    assert register.status_code == 200
    user_id = register.json()["id"]

    assert (
        client.delete(
            f"/admin/users/{user_id}", headers=test_admin["headers"]
        ).status_code
        == 200
    )

    anonymous_response = client.post(f"/admin/users/{user_id}/restore")
    assert anonymous_response.status_code == 401

    # Users have no owning-teacher concept: any teacher is denied, not just
    # a "non-owner" one.
    teacher_response = client.post(
        f"/admin/users/{user_id}/restore", headers=test_teacher["headers"]
    )
    assert teacher_response.status_code == 403

    admin_response = client.post(
        f"/admin/users/{user_id}/restore", headers=test_admin["headers"]
    )
    assert admin_response.status_code == 200
    restored = _get_including_deleted(db, User, user_id)
    assert restored.deleted_at is None
    assert restored.deleted_by_id is None


def test_restore_user_window_boundary_and_not_found(client, db, test_admin):
    email = f"restore_boundary_{uuid.uuid4()}@example.com"
    register = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Boundary Student",
            "role": "student",
            "password": "testpassword",
        },
    )
    assert register.status_code == 200
    user_id = register.json()["id"]

    active_response = client.post(
        f"/admin/users/{user_id}/restore", headers=test_admin["headers"]
    )
    assert active_response.status_code == 404
    assert active_response.json()["error_code"] == "USER_NOT_FOUND"

    missing_response = client.post(
        f"/admin/users/{uuid.uuid4()}/restore", headers=test_admin["headers"]
    )
    assert missing_response.status_code == 404
    assert missing_response.json()["error_code"] == "USER_NOT_FOUND"

    assert (
        client.delete(
            f"/admin/users/{user_id}", headers=test_admin["headers"]
        ).status_code
        == 200
    )
    expired = datetime.now(timezone.utc) - RESTORE_WINDOW
    _set_deleted_at(db, User, user_id, expired)
    expired_response = client.post(
        f"/admin/users/{user_id}/restore", headers=test_admin["headers"]
    )
    assert expired_response.status_code == 409
    assert expired_response.json()["error_code"] == "USER_RESTORE_WINDOW_EXPIRED"
