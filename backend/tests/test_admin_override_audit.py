import uuid

import pytest
from sqlalchemy import select

from app.models.audit_event import AuditEvent
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.services.audit_service import AuditService
from app.services.ai_service import mock_generate_topic_kit
from tests.test_authorization_idor import create_teacher


def test_admin_cross_owner_update_is_audited_without_owner_transfer(
    client,
    db,
    test_teacher,
    test_admin,
):
    created = client.post(
        "/topics",
        json={"name": f"Teacher topic {uuid.uuid4()}"},
        headers=test_teacher["headers"],
    )
    assert created.status_code == 201
    topic_id = uuid.UUID(created.json()["id"])
    request_id = str(uuid.uuid4())

    updated = client.put(
        f"/topics/{topic_id}",
        json={"name": "Admin-reviewed topic"},
        headers={**test_admin["headers"], "X-Request-ID": request_id},
    )

    assert updated.status_code == 200
    db.expire_all()
    topic = db.get(Topic, topic_id)
    assert topic.owner_id == test_teacher["id"]
    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.request_id == request_id,
            AuditEvent.action == "admin.override",
        )
    ).all()
    assert len(events) == 1
    event = events[0]
    assert event.actor_id == test_admin["id"]
    assert event.actor_role == "admin"
    assert event.entity_type == "topic"
    assert event.entity_id == str(topic_id)
    assert event.owner_id == test_teacher["id"]
    assert event.event_metadata == {
        "permission": "update_owned_content",
        "operation": "update",
    }


def test_audit_failure_rolls_back_admin_business_mutation(
    client,
    db,
    test_teacher,
    test_admin,
    monkeypatch,
):
    original_name = f"Atomic topic {uuid.uuid4()}"
    created = client.post(
        "/topics",
        json={"name": original_name},
        headers=test_teacher["headers"],
    )
    topic_id = uuid.UUID(created.json()["id"])
    request_id = str(uuid.uuid4())

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("canary-audit-failure")

    monkeypatch.setattr(AuditService, "record", fail_audit)
    with pytest.raises(RuntimeError, match="canary-audit-failure"):
        client.put(
            f"/topics/{topic_id}",
            json={"name": "Must not persist"},
            headers={**test_admin["headers"], "X-Request-ID": request_id},
        )
    db.expire_all()
    assert db.get(Topic, topic_id).name == original_name
    assert db.scalar(
        select(AuditEvent.event_id).where(AuditEvent.request_id == request_id)
    ) is None


def test_owner_and_denied_mutations_do_not_emit_admin_override(
    client,
    db,
    test_teacher,
):
    created = client.post(
        "/topics",
        json={"name": f"Owner-only topic {uuid.uuid4()}"},
        headers=test_teacher["headers"],
    )
    assert created.status_code == 201
    topic_id = uuid.UUID(created.json()["id"])
    owner_request_id = str(uuid.uuid4())

    owner_update = client.put(
        f"/topics/{topic_id}",
        json={"name": "Owner update"},
        headers={
            **test_teacher["headers"],
            "X-Request-ID": owner_request_id,
        },
    )
    assert owner_update.status_code == 200

    other_teacher = create_teacher(client, db)
    denied_request_id = str(uuid.uuid4())
    denied_update = client.put(
        f"/topics/{topic_id}",
        json={"name": "Denied update"},
        headers={
            **other_teacher["headers"],
            "X-Request-ID": denied_request_id,
        },
    )
    assert denied_update.status_code == 404

    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.request_id.in_(
                [owner_request_id, denied_request_id]
            ),
            AuditEvent.action == "admin.override",
        )
    ).all()
    assert events == []
    db.rollback()


def test_background_admin_override_keeps_originating_request_id(
    db,
    test_teacher,
    test_admin,
    monkeypatch,
):
    topic = Topic(
        owner_id=test_teacher["id"],
        name=f"Background topic {uuid.uuid4()}",
    )
    material = StudyMaterial(
        uploader_id=test_teacher["id"],
        title="background.txt",
        file_type="txt",
        file_path="uploads/materials/background.txt",
        ai_status="completed",
    )
    db.add_all([topic, material])
    db.commit()
    request_id = str(uuid.uuid4())
    monkeypatch.setattr("app.services.ai_service.time.sleep", lambda _seconds: None)

    mock_generate_topic_kit(
        str(material.id),
        str(topic.id),
        str(test_teacher["id"]),
        str(test_admin["id"]),
        request_id,
    )

    db.expire_all()
    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.request_id == request_id,
            AuditEvent.action == "admin.override",
        )
    ).all()
    assert len(events) == 1
    assert events[0].actor_id == test_admin["id"]
    assert events[0].owner_id == test_teacher["id"]
    assert events[0].entity_id == str(topic.id)
