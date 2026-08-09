from datetime import datetime, timezone
import uuid

from pydantic import JsonValue
from sqlalchemy.orm import Session

from app.core.safe_payload import validate_safe_mapping
from app.models.audit_event import AuditEvent
from app.schemas.audit import AuditEventCreate
from app.services.audit_policy import (
    MAX_AUDIT_PAYLOAD_BYTES,
    validate_audit_action_event,
)


def validate_audit_payload(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return validate_safe_mapping(
        payload,
        allowed_top_level_fields=None,
        max_serialized_bytes=MAX_AUDIT_PAYLOAD_BYTES,
    )


class AuditService:
    @staticmethod
    def record(db: Session, event: AuditEventCreate) -> AuditEvent:
        safe_changes, safe_metadata = validate_audit_action_event(
            action=event.action,
            actor_role=event.actor.role,
            entity_type=event.entity.type,
            entity_id=event.entity.id,
            owner_id=event.entity.owner_id,
            outcome=event.outcome,
            changes=event.changes,
            metadata=event.metadata,
        )
        record = AuditEvent(
            event_id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            request_id=event.request_id,
            actor_type=event.actor.actor_type,
            actor_id=event.actor.user_id,
            actor_role=event.actor.role,
            action=event.action,
            entity_type=event.entity.type,
            entity_id=event.entity.id,
            owner_id=event.entity.owner_id,
            outcome=event.outcome,
            changes=safe_changes,
            event_metadata=safe_metadata,
        )
        db.add(record)
        db.flush()
        return record
