"""Add append-only audit events.

Revision ID: b57c9a14d2e8
Revises: e598471b8b6d
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b57c9a14d2e8"
down_revision: Union[str, Sequence[str], None] = "e598471b8b6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUDIT_MUTATION_FUNCTION = "prevent_audit_event_mutation"
AUDIT_MUTATION_TRIGGER = "trg_audit_events_append_only"
AUDIT_TRUNCATE_TRIGGER = "trg_audit_events_no_truncate"


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column(
            "changes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor_type IN ('user', 'system')",
            name="ck_audit_events_actor_type",
        ),
        sa.CheckConstraint(
            "outcome IN ('success', 'denied', 'failure')",
            name="ck_audit_events_outcome",
        ),
        sa.CheckConstraint(
            "length(btrim(request_id)) > 0",
            name="ck_audit_events_request_id_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(action)) > 0",
            name="ck_audit_events_action_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(entity_type)) > 0 AND length(btrim(entity_id)) > 0",
            name="ck_audit_events_entity_not_blank",
        ),
        sa.CheckConstraint(
            "actor_role IN ('admin', 'teacher', 'student', 'system')",
            name="ck_audit_events_actor_role",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(changes) = 'object'",
            name="ck_audit_events_changes_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_audit_events_metadata_object",
        ),
        sa.CheckConstraint(
            "action ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_audit_events_action_format",
        ),
        sa.CheckConstraint(
            "(actor_type = 'system' AND actor_id IS NULL "
            "AND actor_role = 'system') OR "
            "(actor_type = 'user' AND actor_id IS NOT NULL "
            "AND actor_role IS NOT NULL AND actor_role <> 'system')",
            name="ck_audit_events_actor_identity",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_audit_events_action_occurred_at",
        "audit_events",
        ["action", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_actor_id",
        "audit_events",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_owner_occurred_at",
        "audit_events",
        ["owner_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_entity",
        "audit_events",
        ["entity_type", "entity_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_occurred_at",
        "audit_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_request_id",
        "audit_events",
        ["request_id"],
        unique=False,
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {AUDIT_MUTATION_FUNCTION}()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events are append-only' USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {AUDIT_MUTATION_TRIGGER}
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION {AUDIT_MUTATION_FUNCTION}()
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {AUDIT_TRUNCATE_TRIGGER}
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION {AUDIT_MUTATION_FUNCTION}()
        """
    )


def downgrade() -> None:
    op.execute(
        f"DROP TRIGGER IF EXISTS {AUDIT_TRUNCATE_TRIGGER} ON audit_events"
    )
    op.execute(
        f"DROP TRIGGER IF EXISTS {AUDIT_MUTATION_TRIGGER} ON audit_events"
    )
    op.execute(f"DROP FUNCTION IF EXISTS {AUDIT_MUTATION_FUNCTION}()")
    op.drop_index("ix_audit_events_request_id", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_index("ix_audit_events_owner_occurred_at", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_index("ix_audit_events_action_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")
