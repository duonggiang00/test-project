import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, DDL, Index, String, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


AUDIT_MUTATION_FUNCTION = "prevent_audit_event_mutation"
AUDIT_MUTATION_TRIGGER = "trg_audit_events_append_only"
AUDIT_TRUNCATE_TRIGGER = "trg_audit_events_no_truncate"


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('user', 'system')",
            name="ck_audit_events_actor_type",
        ),
        CheckConstraint(
            "outcome IN ('success', 'denied', 'failure')",
            name="ck_audit_events_outcome",
        ),
        CheckConstraint(
            "length(btrim(request_id)) > 0",
            name="ck_audit_events_request_id_not_blank",
        ),
        CheckConstraint(
            "length(btrim(action)) > 0",
            name="ck_audit_events_action_not_blank",
        ),
        CheckConstraint(
            "length(btrim(entity_type)) > 0 AND length(btrim(entity_id)) > 0",
            name="ck_audit_events_entity_not_blank",
        ),
        CheckConstraint(
            "actor_role IN ('admin', 'teacher', 'student', 'system')",
            name="ck_audit_events_actor_role",
        ),
        CheckConstraint(
            "jsonb_typeof(changes) = 'object'",
            name="ck_audit_events_changes_object",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_audit_events_metadata_object",
        ),
        CheckConstraint(
            "action ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_audit_events_action_format",
        ),
        CheckConstraint(
            "(actor_type = 'system' AND actor_id IS NULL "
            "AND actor_role = 'system') OR "
            "(actor_type = 'user' AND actor_id IS NOT NULL "
            "AND actor_role IS NOT NULL AND actor_role <> 'system')",
            name="ck_audit_events_actor_identity",
        ),
        Index(
            "ix_audit_events_entity",
            "entity_type",
            "entity_id",
            "occurred_at",
        ),
        Index(
            "ix_audit_events_action_occurred_at",
            "action",
            "occurred_at",
        ),
        Index(
            "ix_audit_events_owner_occurred_at",
            "owner_id",
            "occurred_at",
        ),
    )

    event_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    request_id = Column(String(64), nullable=False, index=True)
    actor_type = Column(String(16), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_role = Column(String(32), nullable=False)
    action = Column(String(128), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    outcome = Column(String(16), nullable=False)
    changes = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    event_metadata = Column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )


event.listen(
    AuditEvent.__table__,
    "after_create",
    DDL(
        f"""
        CREATE OR REPLACE FUNCTION {AUDIT_MUTATION_FUNCTION}()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events are append-only' USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditEvent.__table__,
    "after_create",
    DDL(
        f"""
        CREATE TRIGGER {AUDIT_MUTATION_TRIGGER}
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION {AUDIT_MUTATION_FUNCTION}()
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditEvent.__table__,
    "after_create",
    DDL(
        f"""
        CREATE TRIGGER {AUDIT_TRUNCATE_TRIGGER}
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION {AUDIT_MUTATION_FUNCTION}()
        """
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditEvent.__table__,
    "before_drop",
    DDL(
        f"DROP TRIGGER IF EXISTS {AUDIT_TRUNCATE_TRIGGER} ON audit_events"
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditEvent.__table__,
    "before_drop",
    DDL(
        f"DROP TRIGGER IF EXISTS {AUDIT_MUTATION_TRIGGER} ON audit_events"
    ).execute_if(dialect="postgresql"),
)
event.listen(
    AuditEvent.__table__,
    "after_drop",
    DDL(f"DROP FUNCTION IF EXISTS {AUDIT_MUTATION_FUNCTION}()")
    .execute_if(dialect="postgresql"),
)
