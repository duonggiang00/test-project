import uuid

import pytest
from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models.audit_event import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.services.audit_service import AuditService


def build_system_event(**overrides):
    values = {
        "request_id": str(uuid.uuid4()),
        "actor": AuditActor(actor_type="system", role="system"),
        "action": "audit.verify",
        "entity": AuditEntity(type="audit_test", id=str(uuid.uuid4())),
        "outcome": "success",
        "changes": {"status": {"before": "pending", "after": "verified"}},
        "metadata": {"test_case": "audit-core"},
    }
    values.update(overrides)
    return AuditEventCreate(**values)


def test_audit_service_persists_timezone_aware_jsonb(db):
    record = AuditService.record(db, build_system_event())
    db.commit()
    db.refresh(record)

    assert record.event_id is not None
    assert record.occurred_at.tzinfo is not None
    assert record.occurred_at.utcoffset() is not None
    assert record.changes["status"]["after"] == "verified"
    assert record.event_metadata == {"test_case": "audit-core"}


def test_business_change_and_audit_roll_back_together(db):
    email = f"audit-rollback-{uuid.uuid4()}@example.test"
    user = User(
        email=email,
        password_hash="not-a-real-password-hash",
        role="teacher",
    )
    db.add(user)
    record = AuditService.record(
        db,
        build_system_event(
            action="user.create",
            entity=AuditEntity(type="user", id=str(user.id or uuid.uuid4())),
            changes={"role": {"before": None, "after": "teacher"}},
            metadata={},
        ),
    )
    event_id = record.event_id

    db.rollback()

    assert db.scalar(select(User).where(User.email == email)) is None
    assert db.get(AuditEvent, event_id) is None


def test_audit_constraint_failure_prevents_business_commit(db):
    email = f"audit-failure-{uuid.uuid4()}@example.test"
    db.add(
        User(
            email=email,
            password_hash="not-a-real-password-hash",
            role="teacher",
        )
    )
    db.add(
        AuditEvent(
            request_id=str(uuid.uuid4()),
            actor_type="system",
            actor_id=uuid.uuid4(),
            actor_role="system",
            action="user.create",
            entity_type="user",
            entity_id=str(uuid.uuid4()),
            outcome="success",
            changes={},
            event_metadata={},
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.scalar(select(User).where(User.email == email)) is None


def test_jsonb_object_constraint_rejects_array_payload(db):
    db.add(
        AuditEvent(
            request_id=str(uuid.uuid4()),
            actor_type="system",
            actor_role="system",
            action="audit.verify",
            entity_type="audit_test",
            entity_id=str(uuid.uuid4()),
            outcome="failure",
            changes=[],
            event_metadata={},
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_trigger_rejects_update_delete_and_truncate(db):
    record = AuditService.record(db, build_system_event())
    db.commit()
    event_id = record.event_id

    with pytest.raises(DBAPIError) as update_error:
        db.execute(
            update(AuditEvent)
            .where(AuditEvent.event_id == event_id)
            .values(outcome="failure")
        )
        db.commit()
    assert update_error.value.orig.pgcode == "55000"
    db.rollback()

    with pytest.raises(DBAPIError) as delete_error:
        db.execute(delete(AuditEvent).where(AuditEvent.event_id == event_id))
        db.commit()
    assert delete_error.value.orig.pgcode == "55000"
    db.rollback()

    with pytest.raises(DBAPIError) as truncate_error:
        db.execute(text("TRUNCATE TABLE audit_events"))
        db.commit()
    assert truncate_error.value.orig.pgcode == "55000"
    db.rollback()

    assert db.get(AuditEvent, event_id) is not None


def test_audit_identifiers_are_denormalized_without_foreign_keys(db):
    inspector = inspect(db.get_bind())

    assert inspector.get_foreign_keys("audit_events") == []

    user = User(
        email=f"audit-denormalized-{uuid.uuid4()}@example.test",
        password_hash="not-a-real-password-hash",
        role="teacher",
    )
    db.add(user)
    db.flush()
    record = AuditService.record(
        db,
        AuditEventCreate(
            request_id=str(uuid.uuid4()),
            actor=AuditActor(actor_type="user", user_id=user.id, role="teacher"),
            action="exam.publish",
            entity=AuditEntity(
                type="exam",
                id=str(uuid.uuid4()),
                owner_id=user.id,
            ),
            outcome="success",
            changes={"is_published": {"before": False, "after": True}},
        ),
    )
    db.commit()
    event_id = record.event_id

    db.delete(user)
    db.commit()

    surviving = db.get(AuditEvent, event_id)
    assert surviving is not None
    assert surviving.actor_id == user.id
    assert surviving.owner_id == user.id
