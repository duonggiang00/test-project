from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic.config import Config
from alembic.script import ScriptDirectory
import psycopg2
from psycopg2.extensions import cursor as PsycopgCursor

if TYPE_CHECKING:
    from scripts.test_database import TestDatabaseManager


MIGRATION_STAGES = (
    ("upgrade-head-1", "upgrade", "head"),
    ("downgrade-base", "downgrade", "base"),
    ("upgrade-head-2", "upgrade", "head"),
)

EXPECTED_HEAD_TABLES = {
    "audit_events",
    "document_chunks",
    "exams",
    "flashcard_decks",
    "flashcard_progress",
    "flashcards",
    "options",
    "questions",
    "study_materials",
    "submission_answers",
    "submissions",
    "topic_briefs",
    "topics",
    "users",
}
EXPECTED_HEAD_ENUMS = {"difficultylevel", "questiontype"}
EXPECTED_BASE_TABLES = {"user"}
EXPECTED_BASE_ENUMS = {"role"}
AUDIT_MUTATION_FUNCTION = "prevent_audit_event_mutation"
AUDIT_MUTATION_TRIGGER = "trg_audit_events_append_only"
AUDIT_TRUNCATE_TRIGGER = "trg_audit_events_no_truncate"
EXPECTED_AUDIT_COLUMN_DEFINITIONS = {
    "event_id": ("uuid", None),
    "occurred_at": ("timestamp with time zone", "now()"),
    "request_id": ("character varying(64)", None),
    "actor_type": ("character varying(16)", None),
    "actor_id": ("uuid", None),
    "actor_role": ("character varying(32)", None),
    "action": ("character varying(128)", None),
    "entity_type": ("character varying(64)", None),
    "entity_id": ("character varying(64)", None),
    "owner_id": ("uuid", None),
    "outcome": ("character varying(16)", None),
    "changes": ("jsonb", "'{}'::jsonb"),
    "metadata": ("jsonb", "'{}'::jsonb"),
}
EXPECTED_AUDIT_COLUMNS = set(EXPECTED_AUDIT_COLUMN_DEFINITIONS)
EXPECTED_AUDIT_NON_NULL_COLUMNS = {
    "action",
    "actor_role",
    "actor_type",
    "changes",
    "entity_id",
    "entity_type",
    "event_id",
    "metadata",
    "occurred_at",
    "outcome",
    "request_id",
}
EXPECTED_AUDIT_INDEX_DEFINITIONS = {
    "audit_events_pkey": (
        True,
        True,
        True,
        True,
        "btree",
        "CREATE UNIQUE INDEX audit_events_pkey ON public.audit_events "
        "USING btree (event_id)",
    ),
    "ix_audit_events_action_occurred_at": (
        False,
        False,
        True,
        True,
        "btree",
        "CREATE INDEX ix_audit_events_action_occurred_at ON "
        "public.audit_events USING btree (action, occurred_at)",
    ),
    "ix_audit_events_actor_id": (
        False,
        False,
        True,
        True,
        "btree",
        "CREATE INDEX ix_audit_events_actor_id ON public.audit_events "
        "USING btree (actor_id)",
    ),
    "ix_audit_events_entity": (
        False,
        False,
        True,
        True,
        "btree",
        "CREATE INDEX ix_audit_events_entity ON public.audit_events USING "
        "btree (entity_type, entity_id, occurred_at)",
    ),
    "ix_audit_events_occurred_at": (
        False,
        False,
        True,
        True,
        "btree",
        "CREATE INDEX ix_audit_events_occurred_at ON public.audit_events "
        "USING btree (occurred_at)",
    ),
    "ix_audit_events_owner_occurred_at": (
        False,
        False,
        True,
        True,
        "btree",
        "CREATE INDEX ix_audit_events_owner_occurred_at ON "
        "public.audit_events USING btree (owner_id, occurred_at)",
    ),
    "ix_audit_events_request_id": (
        False,
        False,
        True,
        True,
        "btree",
        "CREATE INDEX ix_audit_events_request_id ON public.audit_events "
        "USING btree (request_id)",
    ),
}
EXPECTED_AUDIT_CONSTRAINT_DEFINITIONS = {
    "audit_events_pkey": (
        "p",
        True,
        False,
        False,
        "PRIMARY KEY (event_id)",
    ),
    "ck_audit_events_action_format": (
        "c",
        True,
        False,
        False,
        r"CHECK (action::text ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'::text)",
    ),
    "ck_audit_events_action_not_blank": (
        "c",
        True,
        False,
        False,
        "CHECK (length(btrim(action::text)) > 0)",
    ),
    "ck_audit_events_actor_identity": (
        "c",
        True,
        False,
        False,
        "CHECK (actor_type::text = 'system'::text AND actor_id IS NULL AND "
        "actor_role::text = 'system'::text OR actor_type::text = "
        "'user'::text AND actor_id IS NOT NULL AND actor_role IS NOT NULL "
        "AND actor_role::text <> 'system'::text)",
    ),
    "ck_audit_events_actor_role": (
        "c",
        True,
        False,
        False,
        "CHECK (actor_role::text = ANY (ARRAY['admin'::character varying, "
        "'teacher'::character varying, 'student'::character varying, "
        "'system'::character varying]::text[]))",
    ),
    "ck_audit_events_actor_type": (
        "c",
        True,
        False,
        False,
        "CHECK (actor_type::text = ANY (ARRAY['user'::character varying, "
        "'system'::character varying]::text[]))",
    ),
    "ck_audit_events_changes_object": (
        "c",
        True,
        False,
        False,
        "CHECK (jsonb_typeof(changes) = 'object'::text)",
    ),
    "ck_audit_events_entity_not_blank": (
        "c",
        True,
        False,
        False,
        "CHECK (length(btrim(entity_type::text)) > 0 AND "
        "length(btrim(entity_id::text)) > 0)",
    ),
    "ck_audit_events_metadata_object": (
        "c",
        True,
        False,
        False,
        "CHECK (jsonb_typeof(metadata) = 'object'::text)",
    ),
    "ck_audit_events_outcome": (
        "c",
        True,
        False,
        False,
        "CHECK (outcome::text = ANY (ARRAY['success'::character varying, "
        "'denied'::character varying, 'failure'::character varying]::text[]))",
    ),
    "ck_audit_events_request_id_not_blank": (
        "c",
        True,
        False,
        False,
        "CHECK (length(btrim(request_id::text)) > 0)",
    ),
}
EXPECTED_AUDIT_TRIGGER_FRAGMENTS = {
    AUDIT_MUTATION_TRIGGER: (
        "before",
        "delete",
        "update",
        "for each row",
        f"execute function {AUDIT_MUTATION_FUNCTION}()",
    ),
    AUDIT_TRUNCATE_TRIGGER: (
        "before truncate",
        "for each statement",
        f"execute function {AUDIT_MUTATION_FUNCTION}()",
    ),
}
DATABASE_SIGNATURE_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "database-model-signature.json"
)


def build_manager() -> TestDatabaseManager:
    os.environ["ENV"] = "test"
    from scripts.test_database import build_manager as create_manager

    return create_manager()


def validate_expected_head(
    script_heads: set[str], signature_heads: set[str]
) -> str:
    if len(script_heads) != 1:
        raise RuntimeError(
            f"Expected exactly one Alembic head, got {sorted(script_heads)}"
        )
    if len(signature_heads) != 1:
        raise RuntimeError(
            "Database model signature must contain exactly one Alembic head, "
            f"got {sorted(signature_heads)}"
        )
    if script_heads != signature_heads:
        raise RuntimeError(
            "Alembic graph and database model signature disagree: "
            f"graph={sorted(script_heads)} signature={sorted(signature_heads)}"
        )
    return next(iter(script_heads))


def expected_head() -> str:
    configuration = Config("alembic.ini")
    script_heads = set(ScriptDirectory.from_config(configuration).get_heads())
    signature: Any = json.loads(DATABASE_SIGNATURE_PATH.read_text(encoding="utf-8"))
    raw_signature_heads = signature.get("alembic_heads")
    if not isinstance(raw_signature_heads, list) or not all(
        isinstance(head, str) for head in raw_signature_heads
    ):
        raise RuntimeError("Database model signature has invalid alembic_heads")
    return validate_expected_head(script_heads, set(raw_signature_heads))


def current_revisions(cursor: PsycopgCursor) -> set[str]:
    cursor.execute("SELECT to_regclass('public.alembic_version')")
    if cursor.fetchone()[0] is None:
        return set()
    cursor.execute("SELECT version_num FROM alembic_version")
    return {row[0] for row in cursor.fetchall()}


def public_table_names(cursor: PsycopgCursor) -> set[str]:
    cursor.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> 'alembic_version'
        """
    )
    return {row[0] for row in cursor.fetchall()}


def public_enum_names(cursor: PsycopgCursor) -> set[str]:
    cursor.execute(
        """
        SELECT pg_type.typname
        FROM pg_type
        JOIN pg_namespace ON pg_namespace.oid = pg_type.typnamespace
        WHERE pg_namespace.nspname = 'public' AND pg_type.typtype = 'e'
        """,
    )
    return {row[0] for row in cursor.fetchall()}


def audit_function_exists(cursor: PsycopgCursor) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_proc
            JOIN pg_namespace ON pg_namespace.oid = pg_proc.pronamespace
            WHERE pg_namespace.nspname = 'public'
              AND pg_proc.proname = %s
              AND pg_proc.prorettype = 'trigger'::regtype
              AND pg_get_function_identity_arguments(pg_proc.oid) = ''
        )
        """,
        (AUDIT_MUTATION_FUNCTION,),
    )
    return bool(cursor.fetchone()[0])


def audit_trigger_definitions(cursor: PsycopgCursor) -> dict[str, str]:
    cursor.execute(
        """
        SELECT pg_trigger.tgname, pg_get_triggerdef(pg_trigger.oid, true)
        FROM pg_trigger
        JOIN pg_class ON pg_class.oid = pg_trigger.tgrelid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND pg_class.relname = 'audit_events'
          AND NOT pg_trigger.tgisinternal
        """,
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


def audit_column_definitions(
    cursor: PsycopgCursor,
) -> dict[str, tuple[str, str | None]]:
    cursor.execute(
        """
        SELECT
            pg_attribute.attname,
            format_type(pg_attribute.atttypid, pg_attribute.atttypmod),
            pg_get_expr(pg_attrdef.adbin, pg_attrdef.adrelid)
        FROM pg_attribute
        JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        LEFT JOIN pg_attrdef
          ON pg_attrdef.adrelid = pg_attribute.attrelid
         AND pg_attrdef.adnum = pg_attribute.attnum
        WHERE pg_namespace.nspname = 'public'
          AND pg_class.relname = 'audit_events'
          AND pg_attribute.attnum > 0
          AND NOT pg_attribute.attisdropped
        """
    )
    return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}


def audit_index_definitions(
    cursor: PsycopgCursor,
) -> dict[str, tuple[bool, bool, bool, bool, str, str]]:
    cursor.execute(
        """
        SELECT
            index_class.relname,
            pg_index.indisunique,
            pg_index.indisprimary,
            pg_index.indisvalid,
            pg_index.indisready,
            pg_am.amname,
            pg_get_indexdef(index_class.oid)
        FROM pg_index
        JOIN pg_class AS index_class
          ON index_class.oid = pg_index.indexrelid
        JOIN pg_class AS table_class
          ON table_class.oid = pg_index.indrelid
        JOIN pg_namespace
          ON pg_namespace.oid = table_class.relnamespace
        JOIN pg_am
          ON pg_am.oid = index_class.relam
        WHERE pg_namespace.nspname = 'public'
          AND table_class.relname = 'audit_events'
        """
    )
    return {
        row[0]: (row[1], row[2], row[3], row[4], row[5], row[6])
        for row in cursor.fetchall()
    }


def audit_non_nullable_column_names(cursor: PsycopgCursor) -> set[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'audit_events'
          AND is_nullable = 'NO'
        """
    )
    return {row[0] for row in cursor.fetchall()}


def audit_constraint_definitions(
    cursor: PsycopgCursor,
) -> dict[str, tuple[str, bool, bool, bool, str]]:
    cursor.execute(
        """
        SELECT
            pg_constraint.conname,
            pg_constraint.contype,
            pg_constraint.convalidated,
            pg_constraint.condeferrable,
            pg_constraint.condeferred,
            pg_get_constraintdef(pg_constraint.oid, true)
        FROM pg_constraint
        JOIN pg_class ON pg_class.oid = pg_constraint.conrelid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND pg_class.relname = 'audit_events'
          AND pg_constraint.contype <> 'n'
        """
    )
    return {
        row[0]: (row[1], row[2], row[3], row[4], row[5])
        for row in cursor.fetchall()
    }


def normalize_sql(definition: str) -> str:
    return " ".join(definition.split())


def validate_definition_fragments(
    *,
    object_kind: str,
    name: str,
    definition: str,
    expected_fragments: tuple[str, ...],
) -> None:
    normalized_definition = normalize_sql(definition).casefold()
    missing_fragments = [
        fragment
        for fragment in expected_fragments
        if normalize_sql(fragment).casefold() not in normalized_definition
    ]
    if missing_fragments:
        raise RuntimeError(
            f"Unexpected audit {object_kind} definition for {name}: "
            f"missing={missing_fragments} actual={definition!r}"
        )


def validate_audit_schema_state(
    revision: str,
    *,
    column_definitions: dict[str, tuple[str, str | None]],
    non_nullable_columns: set[str],
    index_definitions: dict[str, tuple[bool, bool, bool, bool, str, str]],
    constraint_definitions: dict[str, tuple[str, bool, bool, bool, str]],
) -> None:
    expected_column_definitions = (
        EXPECTED_AUDIT_COLUMN_DEFINITIONS if revision == "head" else {}
    )
    expected_non_nullable_columns = (
        EXPECTED_AUDIT_NON_NULL_COLUMNS if revision == "head" else set()
    )
    expected_index_definitions = (
        EXPECTED_AUDIT_INDEX_DEFINITIONS if revision == "head" else {}
    )
    expected_constraint_definitions = (
        EXPECTED_AUDIT_CONSTRAINT_DEFINITIONS if revision == "head" else {}
    )
    comparisons = (
        (
            "column definitions",
            column_definitions,
            expected_column_definitions,
        ),
        (
            "non-null columns",
            non_nullable_columns,
            expected_non_nullable_columns,
        ),
    )
    for label, actual, expected in comparisons:
        if actual != expected:
            raise RuntimeError(
                f"Unexpected audit {label} at {revision}: "
                f"expected={expected!r} actual={actual!r}"
            )

    normalized_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in index_definitions.items()
    }
    normalized_expected_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in expected_index_definitions.items()
    }
    if normalized_indexes != normalized_expected_indexes:
        raise RuntimeError(
            f"Unexpected audit index definitions at {revision}: "
            f"expected={normalized_expected_indexes!r} "
            f"actual={normalized_indexes!r}"
        )

    normalized_constraints = {
        name: (*definition[:4], normalize_sql(definition[4]))
        for name, definition in constraint_definitions.items()
    }
    normalized_expected_constraints = {
        name: (*definition[:4], normalize_sql(definition[4]))
        for name, definition in expected_constraint_definitions.items()
    }
    if normalized_constraints != normalized_expected_constraints:
        raise RuntimeError(
            f"Unexpected audit constraint definitions at {revision}: "
            f"expected={normalized_expected_constraints!r} "
            f"actual={normalized_constraints!r}"
        )


def validate_schema_state(
    revision: str,
    *,
    head: str,
    revisions: set[str],
    tables: set[str],
    enums: set[str],
    audit_function: bool,
    audit_triggers: dict[str, str],
) -> None:
    if revision == "head":
        if revisions != {head}:
            raise RuntimeError(
                f"Expected Alembic head {head}, got {sorted(revisions)}"
            )
        expected_tables = EXPECTED_HEAD_TABLES
        expected_enums = EXPECTED_HEAD_ENUMS
        expected_audit_function = True
        expected_audit_triggers = set(EXPECTED_AUDIT_TRIGGER_FRAGMENTS)
    elif revision == "base":
        if revisions:
            raise RuntimeError(
                f"Expected no Alembic revision at base, got {sorted(revisions)}"
            )
        expected_tables = EXPECTED_BASE_TABLES
        expected_enums = EXPECTED_BASE_ENUMS
        expected_audit_function = False
        expected_audit_triggers = set()
    else:
        raise RuntimeError(f"Unsupported schema assertion revision: {revision}")

    if tables != expected_tables:
        raise RuntimeError(
            f"Unexpected public tables at {revision}: "
            f"expected={sorted(expected_tables)} actual={sorted(tables)}"
        )
    if enums != expected_enums:
        raise RuntimeError(
            f"Unexpected public enums at {revision}: "
            f"expected={sorted(expected_enums)} actual={sorted(enums)}"
        )
    if audit_function is not expected_audit_function:
        raise RuntimeError(
            f"Unexpected audit mutation function state at {revision}: "
            f"expected={expected_audit_function} actual={audit_function}"
        )
    if set(audit_triggers) != expected_audit_triggers:
        raise RuntimeError(
            f"Unexpected audit mutation triggers at {revision}: "
            f"expected={sorted(expected_audit_triggers)} "
            f"actual={sorted(audit_triggers)}"
        )
    if revision == "head":
        for name, fragments in EXPECTED_AUDIT_TRIGGER_FRAGMENTS.items():
            validate_definition_fragments(
                object_kind="trigger",
                name=name,
                definition=audit_triggers[name],
                expected_fragments=fragments,
            )


def assert_schema_state(manager: TestDatabaseManager, revision: str) -> None:
    head = expected_head()
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            revisions = current_revisions(cursor)
            tables = public_table_names(cursor)
            enums = public_enum_names(cursor)
            audit_function = audit_function_exists(cursor)
            audit_triggers = audit_trigger_definitions(cursor)
            audit_columns = audit_column_definitions(cursor)
            audit_non_nullable_columns = audit_non_nullable_column_names(cursor)
            audit_indexes = audit_index_definitions(cursor)
            audit_constraints = audit_constraint_definitions(cursor)
    finally:
        connection.close()

    validate_schema_state(
        revision,
        head=head,
        revisions=revisions,
        tables=tables,
        enums=enums,
        audit_function=audit_function,
        audit_triggers=audit_triggers,
    )
    validate_audit_schema_state(
        revision,
        column_definitions=audit_columns,
        non_nullable_columns=audit_non_nullable_columns,
        index_definitions=audit_indexes,
        constraint_definitions=audit_constraints,
    )

    print(
        "MIGRATION_SCHEMA_ASSERTIONS_PASSED "
        f"revision={revision} revisions={','.join(sorted(revisions)) or 'base'} "
        f"tables={len(tables)} enums={','.join(sorted(enums))} "
        f"audit_function={str(audit_function).lower()} "
        f"audit_triggers={len(audit_triggers)} "
        f"audit_columns={len(audit_columns)} "
        f"audit_non_null={len(audit_non_nullable_columns)} "
        f"audit_indexes={len(audit_indexes)} "
        f"audit_constraints={len(audit_constraints)}",
        flush=True,
    )


def assert_audit_append_only(
    manager: TestDatabaseManager,
    revision: str,
) -> None:
    if revision != "head":
        return

    event_id = uuid.uuid4()
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_events (
                    event_id,
                    request_id,
                    actor_type,
                    actor_role,
                    action,
                    entity_type,
                    entity_id,
                    outcome
                )
                VALUES (%s, %s, 'system', 'system', 'migration.verify',
                        'migration', %s, 'success')
                """,
                (str(event_id), f"migration-{event_id.hex}", str(event_id)),
            )
        connection.commit()

        statements = (
            (
                "UPDATE",
                "UPDATE audit_events SET outcome = 'failure' WHERE event_id = %s",
                (str(event_id),),
            ),
            (
                "DELETE",
                "DELETE FROM audit_events WHERE event_id = %s",
                (str(event_id),),
            ),
            ("TRUNCATE", "TRUNCATE TABLE audit_events", None),
        )
        for operation, statement, parameters in statements:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(statement, parameters)
                connection.commit()
            except psycopg2.Error as exc:
                connection.rollback()
                if exc.pgcode != "55000":
                    raise RuntimeError(
                        "Audit append-only trigger returned an unexpected "
                        f"SQLSTATE for {operation}: {exc.pgcode}"
                    ) from exc
            else:
                raise RuntimeError(
                    f"Audit append-only trigger allowed {operation}"
                )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM audit_events WHERE event_id = %s)",
                (str(event_id),),
            )
            if not cursor.fetchone()[0]:
                raise RuntimeError(
                    "Audit append-only verification event was not preserved"
                )
    finally:
        connection.close()

    print("MIGRATION_AUDIT_APPEND_ONLY_ASSERTION_PASSED", flush=True)


def main() -> int:
    manager = build_manager()
    manager.create()
    try:
        for stage_name, action, revision in MIGRATION_STAGES:
            print(f"MIGRATION_STAGE_STARTED stage={stage_name}", flush=True)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    "alembic.ini",
                    action,
                    revision,
                ],
                check=False,
            )
            if completed.returncode != 0:
                print(
                    f"MIGRATION_STAGE_FAILED stage={stage_name} "
                    f"exit_code={completed.returncode}",
                    flush=True,
                )
                return completed.returncode
            assert_schema_state(manager, revision)
            assert_audit_append_only(manager, revision)
            print(f"MIGRATION_STAGE_PASSED stage={stage_name}", flush=True)
        return 0
    finally:
        manager.drop_created()


if __name__ == "__main__":
    raise SystemExit(main())
