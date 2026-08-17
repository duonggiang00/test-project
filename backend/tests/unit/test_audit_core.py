from copy import deepcopy
import math
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.audit import AuditActor, AuditEntity, AuditEventCreate
from app.services.audit_service import AuditService, validate_audit_payload


def build_event(**overrides):
    values = {
        "request_id": str(uuid.uuid4()),
        "actor": AuditActor(
            actor_type="user",
            user_id=uuid.uuid4(),
            role="teacher",
        ),
        "action": "exam.publish",
        "entity": AuditEntity(
            type="exam",
            id=str(uuid.uuid4()),
            owner_id=uuid.uuid4(),
        ),
        "outcome": "success",
        "changes": {"is_published": {"before": False, "after": True}},
        "metadata": {"context_source_ids": [str(uuid.uuid4())]},
    }
    values.update(overrides)
    return AuditEventCreate(**values)


class FakeSession:
    def __init__(self, flush_error=None):
        self.added = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.flush_error = flush_error

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_calls += 1
        if self.flush_error:
            raise self.flush_error

    def commit(self):
        self.commit_calls += 1
        raise AssertionError("AuditService must not commit")


def test_audit_actor_and_event_schema_fail_closed():
    with pytest.raises(ValidationError):
        AuditActor(actor_type="system", user_id=uuid.uuid4(), role="system")
    with pytest.raises(ValidationError):
        AuditActor(actor_type="user", user_id=None, role="teacher")
    with pytest.raises(ValidationError):
        build_event(action="publish")
    with pytest.raises(ValidationError):
        build_event(request_id="not-a-request-id")
    with pytest.raises(ValidationError):
        build_event(outcome="unknown")


def test_payload_validation_returns_a_copy_without_mutating_safe_input():
    payload = {
        "is_published": {"before": False, "after": True},
        "context_source_ids": [str(uuid.uuid4())],
        "input_tokens": 120,
    }
    original = deepcopy(payload)

    validated = validate_audit_payload(payload)

    assert validated == original
    assert payload == original
    assert validated is not payload
    assert validated["is_published"] is not payload["is_published"]


@pytest.mark.parametrize(
    "payload",
    [
        {"Password": "canary-password"},
        {"nested": {"refreshToken": "canary-token"}},
        {"nested": {"refreshtoken": "canary-token"}},
        {"nested": {"passwordhash": "canary-password"}},
        {"nested": {"rawprompt": "canary-prompt"}},
        {"nested": {"password_confirmation": "canary-password"}},
        {"nested": {"authorization_header": "canary-authorization"}},
        {"nested": {"provider_error": "canary-provider-error"}},
        {"original_filename": "private.pdf"},
        {"path": "/srv/private/document.txt"},
        {"client_ip": "203.0.113.10"},
        {"raw_document_content": "canary-document"},
        {"note": "Bearer secret-token"},
        {"note": "sk-providerSecret123"},
        {"note": "https://user:password@example.test/path"},
        {"note": "session_cookie=secret"},
        {"note": "C:\\private\\document.txt"},
        {"note": "/srv/private/document.txt"},
        {"note": "/var/lib/private/document.txt"},
        {"note": "../private/document.txt"},
        {"note": r"\\server\private\document.txt"},
        {"note": "file:///srv/private/document.txt"},
        {"note": "teacher@example.test"},
        {"note": "curl/8.0"},
        {"note": "203.0.113.10"},
        {"note": "client=2001:db8::1"},
        {"actor_email": "person@example.test"},
        {"raw_prompt": "sensitive prompt"},
    ],
)
def test_payload_validation_rejects_sensitive_keys_and_values(payload):
    with pytest.raises(ValueError, match="forbidden") as raised:
        validate_audit_payload(payload)

    assert "canary" not in str(raised.value).casefold()
    assert "secret" not in str(raised.value).casefold()


def test_payload_validation_rejects_non_json_depth_size_and_cycles():
    with pytest.raises(ValueError, match="non-JSON"):
        validate_audit_payload({"value": b"bytes"})
    with pytest.raises(ValueError, match="non-finite"):
        validate_audit_payload({"value": math.inf})

    deep = {}
    cursor = deep
    for index in range(14):
        key = f"level_{index}"
        cursor[key] = {}
        cursor = cursor[key]
    with pytest.raises(ValueError, match="nesting depth"):
        validate_audit_payload(deep)

    with pytest.raises(ValueError, match="serialized size"):
        validate_audit_payload({"value": "x" * (33 * 1024)})

    cyclic = {}
    cyclic["self"] = cyclic
    with pytest.raises(ValueError, match="cyclic"):
        validate_audit_payload(cyclic)


def test_audit_service_adds_and_flushes_without_committing():
    session = FakeSession()
    event = build_event()

    record = AuditService.record(session, event)

    assert session.added == [record]
    assert session.flush_calls == 1
    assert session.commit_calls == 0
    assert record.event_id is not None
    assert record.occurred_at.tzinfo is not None
    assert record.occurred_at.utcoffset() is not None
    assert record.actor_id == event.actor.user_id
    assert record.owner_id == event.entity.owner_id
    assert record.event_metadata == event.metadata


def test_audit_service_requires_an_action_specific_payload_policy():
    unknown_session = FakeSession()
    with pytest.raises(ValueError, match="no registered event policy"):
        AuditService.record(
            unknown_session,
            build_event(action="exam.unregistered_action"),
        )
    assert unknown_session.added == []
    assert unknown_session.flush_calls == 0

    extra_field_session = FakeSession()
    with pytest.raises(ValueError, match="outside its allowlist"):
        AuditService.record(
            extra_field_session,
            build_event(changes={"unreviewed_field": True}),
        )
    assert extra_field_session.added == []
    assert extra_field_session.flush_calls == 0

    wrong_shape_session = FakeSession()
    with pytest.raises(ValueError, match="action-specific schema") as raised:
        AuditService.record(
            wrong_shape_session,
            build_event(
                changes={
                    "is_published": {
                        "before": "canary-unreviewed-content",
                        "after": True,
                    }
                }
            ),
        )
    assert "canary" not in str(raised.value).casefold()
    assert wrong_shape_session.added == []
    assert wrong_shape_session.flush_calls == 0


@pytest.mark.parametrize(
    "event",
    [
        build_event(
            entity=AuditEntity(
                type="exam",
                id="teacher@example.test",
                owner_id=uuid.uuid4(),
            )
        ),
        build_event(
            entity=AuditEntity(
                type="user",
                id=str(uuid.uuid4()),
                owner_id=uuid.uuid4(),
            )
        ),
        build_event(
            actor=AuditActor(
                actor_type="user",
                user_id=uuid.uuid4(),
                role="student",
            )
        ),
        build_event(
            entity=AuditEntity(type="exam", id=str(uuid.uuid4()))
        ),
        build_event(changes={}),
    ],
)
def test_audit_service_rejects_invalid_event_semantics_before_persistence(event):
    session = FakeSession()

    with pytest.raises(ValueError, match="action-specific schema") as raised:
        AuditService.record(session, event)

    assert "teacher@example.test" not in str(raised.value)
    assert session.added == []
    assert session.flush_calls == 0


def test_audit_service_propagates_flush_failure_without_committing():
    session = FakeSession(flush_error=RuntimeError("database unavailable"))

    with pytest.raises(RuntimeError, match="database unavailable"):
        AuditService.record(session, build_event())

    assert session.flush_calls == 1
    assert session.commit_calls == 0


def test_admin_override_policy_accepts_only_narrow_safe_metadata():
    session = FakeSession()
    owner_id = uuid.uuid4()
    event = build_event(
        actor=AuditActor(
            actor_type="user",
            user_id=uuid.uuid4(),
            role="admin",
        ),
        action="admin.override",
        entity=AuditEntity(
            type="exam",
            id=str(uuid.uuid4()),
            owner_id=owner_id,
        ),
        changes={},
        metadata={
            "permission": "update_owned_content",
            "operation": "update",
        },
    )

    record = AuditService.record(session, event)

    assert record.owner_id == owner_id
    assert record.action == "admin.override"
    assert record.event_metadata == event.metadata


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "actor": AuditActor(
                actor_type="user",
                user_id=uuid.uuid4(),
                role="teacher",
            )
        },
        {"metadata": {"operation": "update"}},
        {
            "metadata": {
                "permission": "update_owned_content",
                "operation": "arbitrary_operation",
            }
        },
        {"changes": {"content": {"before": None, "after": "canary"}}},
    ],
)
def test_admin_override_policy_fails_closed(overrides):
    event_values = {
        "actor": AuditActor(
            actor_type="user",
            user_id=uuid.uuid4(),
            role="admin",
        ),
        "action": "admin.override",
        "entity": AuditEntity(
            type="topic",
            id=str(uuid.uuid4()),
            owner_id=None,
        ),
        "changes": {},
        "metadata": {
            "permission": "delete_owned_content",
            "operation": "delete",
        },
    }
    event_values.update(overrides)
    session = FakeSession()

    with pytest.raises(
        ValueError,
        match="action-specific schema|outside its allowlist",
    ) as raised:
        AuditService.record(session, build_event(**event_values))

    assert "canary" not in str(raised.value).casefold()
    assert session.added == []
