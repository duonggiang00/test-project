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


OWNERSHIP_PREVIOUS_REVISION = "b57c9a14d2e8"
SINGLE_CHOICE_PREVIOUS_REVISION = "ca82f9a51d44"
RAG_PREVIOUS_REVISION = "a74c9d2e6f10"
SOFT_DELETE_PREVIOUS_REVISION = "a83c1d7e9f02"
GRADE_OVERRIDE_PREVIOUS_REVISION = "e7b21c9d4a83"
GRADE_OVERRIDE_COLUMNS = ("override_reason", "overridden_at", "overridden_by_id")
SOFT_DELETE_TABLES = (
    "users",
    "topics",
    "exams",
    "questions",
    "study_materials",
)
MIGRATION_STAGES = (
    (
        "upgrade-ownership-previous-head",
        "upgrade",
        OWNERSHIP_PREVIOUS_REVISION,
    ),
    (
        "upgrade-single-choice-previous-head",
        "upgrade",
        SINGLE_CHOICE_PREVIOUS_REVISION,
    ),
    ("upgrade-rag-previous-head", "upgrade", RAG_PREVIOUS_REVISION),
    ("upgrade-head-1", "upgrade", "head"),
    ("downgrade-rag-previous-head", "downgrade", RAG_PREVIOUS_REVISION),
    ("downgrade-base", "downgrade", "base"),
    ("upgrade-head-2", "upgrade", "head"),
)

EXPECTED_HEAD_TABLES = {
    "ai_generation_jobs",
    "ai_grade_suggestions",
    "ai_restricted_payloads",
    "audit_events",
    "document_chunks",
    "exams",
    "flashcard_decks",
    "flashcard_progress",
    "flashcards",
    "options",
    "purge_jobs",
    "questions",
    "refresh_sessions",
    "study_materials",
    "submission_answers",
    "submissions",
    "topic_briefs",
    "topics",
    "users",
}
EXPECTED_HEAD_ENUMS = {"difficultylevel", "questiontype"}
EXPECTED_HEAD_ENUM_LABELS: dict[str, tuple[str, ...]] = {
    "difficultylevel": ("EASY", "MEDIUM", "HARD"),
    "questiontype": (
        "SINGLE_CHOICE",
        "MULTIPLE_CHOICE",
        "MATCHING",
        "FILL_IN_BLANK",
    ),
}
EXPECTED_BASE_TABLES = {"user"}
EXPECTED_BASE_ENUMS = {"role"}
EXPECTED_BASE_ENUM_LABELS: dict[str, tuple[str, ...]] = {
    "role": ("ADMIN", "USER")
}
EXPECTED_QUESTION_TYPE_COLUMN = (
    "USER-DEFINED",
    "questiontype",
    False,
    "'MULTIPLE_CHOICE'::questiontype",
)
EXPECTED_RAG_INDEX_FRAGMENTS: dict[str, tuple[str, ...]] = {
    "ix_document_chunks_material_id": ("document_chunks", "(material_id)"),
    "ix_document_chunks_embedding_hnsw": (
        "document_chunks",
        "USING hnsw",
        "embedding",
        "vector_cosine_ops",
    ),
    "ix_document_chunks_content_fts": (
        "document_chunks",
        "USING gin",
        "to_tsvector",
        "content",
    ),
}
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
EXPECTED_OWNERSHIP_COLUMN_DEFINITIONS = {
    ("questions", "owner_id"): ("uuid", True, None),
    ("topics", "owner_id"): ("uuid", True, None),
}
EXPECTED_OWNERSHIP_FOREIGN_KEY_DEFINITIONS = {
    "questions_owner_id_fkey": (
        "questions",
        ("owner_id",),
        "users",
        ("id",),
        "r",
        "a",
        True,
        False,
        False,
        "FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE RESTRICT",
    ),
    "topics_owner_id_fkey": (
        "topics",
        ("owner_id",),
        "users",
        ("id",),
        "r",
        "a",
        True,
        False,
        False,
        "FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE RESTRICT",
    ),
}
EXPECTED_OWNERSHIP_INDEX_DEFINITIONS = {
    name: (
        False,
        False,
        True,
        True,
        "btree",
        f"CREATE INDEX {name} ON public.{table} USING btree ({column})",
    )
    for name, table, column in (
        ("ix_document_chunks_material_id", "document_chunks", "material_id"),
        ("ix_exams_creator_id", "exams", "creator_id"),
        ("ix_flashcard_decks_topic_id", "flashcard_decks", "topic_id"),
        ("ix_flashcards_deck_id", "flashcards", "deck_id"),
        ("ix_questions_exam_id", "questions", "exam_id"),
        ("ix_questions_owner_id", "questions", "owner_id"),
        (
            "ix_study_materials_uploader_id",
            "study_materials",
            "uploader_id",
        ),
        ("ix_topic_briefs_topic_id", "topic_briefs", "topic_id"),
        ("ix_topics_owner_id", "topics", "owner_id"),
    )
}
EXPECTED_SOFT_DELETE_COLUMN_DEFINITIONS: dict[
    tuple[str, str], tuple[str, bool, str | None]
] = {
    **{
        (table, "deleted_at"): ("timestamp with time zone", True, None)
        for table in SOFT_DELETE_TABLES
    },
    **{
        (table, "deleted_by_id"): ("uuid", True, None)
        for table in SOFT_DELETE_TABLES
    },
}
EXPECTED_SOFT_DELETE_FOREIGN_KEY_DEFINITIONS = {
    f"{table}_deleted_by_id_fkey": (
        table,
        ("deleted_by_id",),
        "users",
        ("id",),
        "n",
        "a",
        True,
        False,
        False,
        "FOREIGN KEY (deleted_by_id) REFERENCES users(id) ON DELETE SET NULL",
    )
    for table in SOFT_DELETE_TABLES
}
EXPECTED_SOFT_DELETE_INDEX_DEFINITIONS: dict[
    str, tuple[bool, bool, bool, bool, str, str]
] = {}
for _table in SOFT_DELETE_TABLES:
    EXPECTED_SOFT_DELETE_INDEX_DEFINITIONS[f"ix_{_table}_deleted_at"] = (
        False,
        False,
        True,
        True,
        "btree",
        f"CREATE INDEX ix_{_table}_deleted_at ON public.{_table} "
        "USING btree (deleted_at)",
    )
    EXPECTED_SOFT_DELETE_INDEX_DEFINITIONS[f"ix_{_table}_deleted_by_id"] = (
        False,
        False,
        True,
        True,
        "btree",
        f"CREATE INDEX ix_{_table}_deleted_by_id ON public.{_table} "
        "USING btree (deleted_by_id)",
    )
del _table
EXPECTED_GRADE_OVERRIDE_COLUMN_DEFINITIONS: dict[
    tuple[str, str], tuple[str, bool, str | None]
] = {
    ("submission_answers", "override_reason"): ("text", True, None),
    ("submission_answers", "overridden_at"): (
        "timestamp with time zone",
        True,
        None,
    ),
    ("submission_answers", "overridden_by_id"): ("uuid", True, None),
}
EXPECTED_GRADE_OVERRIDE_FOREIGN_KEY_DEFINITIONS = {
    "submission_answers_overridden_by_id_fkey": (
        "submission_answers",
        ("overridden_by_id",),
        "users",
        ("id",),
        "n",
        "a",
        True,
        False,
        False,
        "FOREIGN KEY (overridden_by_id) REFERENCES users(id) ON DELETE SET NULL",
    )
}
EXPECTED_GRADE_OVERRIDE_INDEX_DEFINITIONS: dict[
    str, tuple[bool, bool, bool, bool, str, str]
] = {
    "ix_submission_answers_overridden_by_id": (
        False,
        False,
        True,
        True,
        "btree",
        "CREATE INDEX ix_submission_answers_overridden_by_id ON "
        "public.submission_answers USING btree (overridden_by_id)",
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


def public_enum_labels(cursor: PsycopgCursor) -> dict[str, tuple[str, ...]]:
    cursor.execute(
        """
        SELECT pg_type.typname, pg_enum.enumlabel
        FROM pg_type
        JOIN pg_namespace ON pg_namespace.oid = pg_type.typnamespace
        JOIN pg_enum ON pg_enum.enumtypid = pg_type.oid
        WHERE pg_namespace.nspname = 'public'
        ORDER BY pg_type.typname, pg_enum.enumsortorder
        """,
    )
    labels: dict[str, list[str]] = {}
    for enum_name, label in cursor.fetchall():
        labels.setdefault(enum_name, []).append(label)
    return {name: tuple(values) for name, values in labels.items()}


def question_type_column_definition(
    cursor: PsycopgCursor,
) -> tuple[str, str, bool, str | None] | None:
    cursor.execute(
        """
        SELECT data_type, udt_name, is_nullable = 'YES', column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'questions'
          AND column_name = 'question_type'
        """,
    )
    return cursor.fetchone()


def validate_question_type_schema_state(
    revision: str,
    *,
    enum_labels: dict[str, tuple[str, ...]],
    column_definition: tuple[str, str, bool, str | None] | None,
) -> None:
    expected_labels: dict[str, tuple[str, ...]]
    if revision == "head":
        expected_labels = EXPECTED_HEAD_ENUM_LABELS
        expected_column = EXPECTED_QUESTION_TYPE_COLUMN
    elif revision == "base":
        expected_labels = EXPECTED_BASE_ENUM_LABELS
        expected_column = None
    else:
        raise RuntimeError(f"Unsupported question-type assertion revision: {revision}")
    if enum_labels != expected_labels:
        raise RuntimeError(
            f"Unexpected public enum labels at {revision}: "
            f"expected={expected_labels!r} actual={enum_labels!r}"
        )
    if column_definition != expected_column:
        raise RuntimeError(
            f"Unexpected question_type column definition at {revision}: "
            f"expected={expected_column!r} actual={column_definition!r}"
        )


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


def ownership_column_definitions(
    cursor: PsycopgCursor,
) -> dict[tuple[str, str], tuple[str, bool, str | None]]:
    cursor.execute(
        """
        SELECT
            pg_class.relname,
            pg_attribute.attname,
            format_type(pg_attribute.atttypid, pg_attribute.atttypmod),
            NOT pg_attribute.attnotnull,
            pg_get_expr(pg_attrdef.adbin, pg_attrdef.adrelid)
        FROM pg_attribute
        JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        LEFT JOIN pg_attrdef
          ON pg_attrdef.adrelid = pg_attribute.attrelid
         AND pg_attrdef.adnum = pg_attribute.attnum
        WHERE pg_namespace.nspname = 'public'
          AND pg_class.relname IN ('questions', 'topics')
          AND pg_attribute.attname = 'owner_id'
          AND pg_attribute.attnum > 0
          AND NOT pg_attribute.attisdropped
        """
    )
    return {
        (row[0], row[1]): (row[2], row[3], row[4])
        for row in cursor.fetchall()
    }


def ownership_foreign_key_definitions(
    cursor: PsycopgCursor,
) -> dict[
    str,
    tuple[
        str,
        tuple[str, ...],
        str,
        tuple[str, ...],
        str,
        str,
        bool,
        bool,
        bool,
        str,
    ],
]:
    cursor.execute(
        """
        SELECT
            pg_constraint.conname,
            source_class.relname,
            ARRAY(
                SELECT source_attribute.attname
                FROM unnest(pg_constraint.conkey)
                     WITH ORDINALITY AS source_key(attnum, position)
                JOIN pg_attribute AS source_attribute
                  ON source_attribute.attrelid = pg_constraint.conrelid
                 AND source_attribute.attnum = source_key.attnum
                ORDER BY source_key.position
            ),
            target_class.relname,
            ARRAY(
                SELECT target_attribute.attname
                FROM unnest(pg_constraint.confkey)
                     WITH ORDINALITY AS target_key(attnum, position)
                JOIN pg_attribute AS target_attribute
                  ON target_attribute.attrelid = pg_constraint.confrelid
                 AND target_attribute.attnum = target_key.attnum
                ORDER BY target_key.position
            ),
            pg_constraint.confdeltype,
            pg_constraint.confupdtype,
            pg_constraint.convalidated,
            pg_constraint.condeferrable,
            pg_constraint.condeferred,
            pg_get_constraintdef(pg_constraint.oid, true)
        FROM pg_constraint
        JOIN pg_class AS source_class
          ON source_class.oid = pg_constraint.conrelid
        JOIN pg_class AS target_class
          ON target_class.oid = pg_constraint.confrelid
        JOIN pg_namespace
          ON pg_namespace.oid = source_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND pg_constraint.contype = 'f'
          AND source_class.relname IN ('questions', 'topics')
          AND EXISTS (
              SELECT 1
              FROM unnest(pg_constraint.conkey) AS source_key(attnum)
              JOIN pg_attribute AS source_attribute
                ON source_attribute.attrelid = pg_constraint.conrelid
               AND source_attribute.attnum = source_key.attnum
              WHERE source_attribute.attname = 'owner_id'
          )
        """
    )
    return {
        row[0]: (
            row[1],
            tuple(row[2]),
            row[3],
            tuple(row[4]),
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
        )
        for row in cursor.fetchall()
    }


def ownership_index_definitions(
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
          AND index_class.relname = ANY(%s)
        """,
        (list(EXPECTED_OWNERSHIP_INDEX_DEFINITIONS),),
    )
    return {
        row[0]: (row[1], row[2], row[3], row[4], row[5], row[6])
        for row in cursor.fetchall()
    }


def soft_delete_column_definitions(
    cursor: PsycopgCursor,
) -> dict[tuple[str, str], tuple[str, bool, str | None]]:
    cursor.execute(
        """
        SELECT
            pg_class.relname,
            pg_attribute.attname,
            format_type(pg_attribute.atttypid, pg_attribute.atttypmod),
            NOT pg_attribute.attnotnull,
            pg_get_expr(pg_attrdef.adbin, pg_attrdef.adrelid)
        FROM pg_attribute
        JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        LEFT JOIN pg_attrdef
          ON pg_attrdef.adrelid = pg_attribute.attrelid
         AND pg_attrdef.adnum = pg_attribute.attnum
        WHERE pg_namespace.nspname = 'public'
          AND pg_class.relname = ANY(%s)
          AND pg_attribute.attname IN ('deleted_at', 'deleted_by_id')
          AND pg_attribute.attnum > 0
          AND NOT pg_attribute.attisdropped
        """,
        (list(SOFT_DELETE_TABLES),),
    )
    return {
        (row[0], row[1]): (row[2], row[3], row[4])
        for row in cursor.fetchall()
    }


def grade_override_columns_present(cursor: PsycopgCursor) -> frozenset[str]:
    """Which of the three grade-override-trail columns still exist."""
    cursor.execute(
        """
        SELECT pg_attribute.attname
        FROM pg_attribute
        JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND pg_class.relname = 'submission_answers'
          AND pg_attribute.attname = ANY(%s)
          AND pg_attribute.attnum > 0
          AND NOT pg_attribute.attisdropped
        """,
        (list(GRADE_OVERRIDE_COLUMNS),),
    )
    return frozenset(row[0] for row in cursor.fetchall())


def grade_override_column_definitions(
    cursor: PsycopgCursor,
) -> dict[tuple[str, str], tuple[str, bool, str | None]]:
    """Exact type/nullability/default for the three grade-override columns.

    Mirrors `soft_delete_column_definitions`: existence alone (see
    `grade_override_columns_present`, used only by the downgrade-refusal
    probe) doesn't catch a column that exists with the wrong type or a
    stray default, so a fresh upgrade is checked against the exact shape.
    """
    cursor.execute(
        """
        SELECT
            pg_class.relname,
            pg_attribute.attname,
            format_type(pg_attribute.atttypid, pg_attribute.atttypmod),
            NOT pg_attribute.attnotnull,
            pg_get_expr(pg_attrdef.adbin, pg_attrdef.adrelid)
        FROM pg_attribute
        JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        LEFT JOIN pg_attrdef
          ON pg_attrdef.adrelid = pg_attribute.attrelid
         AND pg_attrdef.adnum = pg_attribute.attnum
        WHERE pg_namespace.nspname = 'public'
          AND pg_class.relname = 'submission_answers'
          AND pg_attribute.attname = ANY(%s)
          AND pg_attribute.attnum > 0
          AND NOT pg_attribute.attisdropped
        """,
        (list(GRADE_OVERRIDE_COLUMNS),),
    )
    return {
        (row[0], row[1]): (row[2], row[3], row[4])
        for row in cursor.fetchall()
    }


def grade_override_foreign_key_definitions(
    cursor: PsycopgCursor,
) -> dict[
    str,
    tuple[
        str,
        tuple[str, ...],
        str,
        tuple[str, ...],
        str,
        str,
        bool,
        bool,
        bool,
        str,
    ],
]:
    """Exact FK shape for `overridden_by_id`, in particular ON DELETE SET NULL.

    Same query shape as `soft_delete_foreign_key_definitions`; the WHERE
    clause narrows to the one grade-override FK by column name.
    """
    cursor.execute(
        """
        SELECT
            pg_constraint.conname,
            source_class.relname,
            ARRAY(
                SELECT source_attribute.attname
                FROM unnest(pg_constraint.conkey)
                     WITH ORDINALITY AS source_key(attnum, position)
                JOIN pg_attribute AS source_attribute
                  ON source_attribute.attrelid = pg_constraint.conrelid
                 AND source_attribute.attnum = source_key.attnum
                ORDER BY source_key.position
            ),
            target_class.relname,
            ARRAY(
                SELECT target_attribute.attname
                FROM unnest(pg_constraint.confkey)
                     WITH ORDINALITY AS target_key(attnum, position)
                JOIN pg_attribute AS target_attribute
                  ON target_attribute.attrelid = pg_constraint.confrelid
                 AND target_attribute.attnum = target_key.attnum
                ORDER BY target_key.position
            ),
            pg_constraint.confdeltype,
            pg_constraint.confupdtype,
            pg_constraint.convalidated,
            pg_constraint.condeferrable,
            pg_constraint.condeferred,
            pg_get_constraintdef(pg_constraint.oid, true)
        FROM pg_constraint
        JOIN pg_class AS source_class
          ON source_class.oid = pg_constraint.conrelid
        JOIN pg_class AS target_class
          ON target_class.oid = pg_constraint.confrelid
        JOIN pg_namespace
          ON pg_namespace.oid = source_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND pg_constraint.contype = 'f'
          AND source_class.relname = 'submission_answers'
          AND EXISTS (
              SELECT 1
              FROM unnest(pg_constraint.conkey) AS source_key(attnum)
              JOIN pg_attribute AS source_attribute
                ON source_attribute.attrelid = pg_constraint.conrelid
               AND source_attribute.attnum = source_key.attnum
              WHERE source_attribute.attname = 'overridden_by_id'
          )
        """
    )
    return {
        row[0]: (
            row[1],
            tuple(row[2]),
            row[3],
            tuple(row[4]),
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
        )
        for row in cursor.fetchall()
    }


def grade_override_index_definitions(
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
          AND index_class.relname = ANY(%s)
        """,
        (list(EXPECTED_GRADE_OVERRIDE_INDEX_DEFINITIONS),),
    )
    return {
        row[0]: (row[1], row[2], row[3], row[4], row[5], row[6])
        for row in cursor.fetchall()
    }


def validate_grade_override_schema_state(
    revision: str,
    *,
    column_definitions: dict[
        tuple[str, str], tuple[str, bool, str | None]
    ],
    foreign_key_definitions: dict[
        str,
        tuple[
            str,
            tuple[str, ...],
            str,
            tuple[str, ...],
            str,
            str,
            bool,
            bool,
            bool,
            str,
        ],
    ],
    index_definitions: dict[str, tuple[bool, bool, bool, bool, str, str]],
) -> None:
    """Exact grade-override schema at head; empty before the migration landed."""
    expected_columns = (
        EXPECTED_GRADE_OVERRIDE_COLUMN_DEFINITIONS if revision == "head" else {}
    )
    expected_foreign_keys = (
        EXPECTED_GRADE_OVERRIDE_FOREIGN_KEY_DEFINITIONS
        if revision == "head"
        else {}
    )
    expected_indexes = (
        EXPECTED_GRADE_OVERRIDE_INDEX_DEFINITIONS if revision == "head" else {}
    )
    if column_definitions != expected_columns:
        raise RuntimeError(
            f"Unexpected grade-override column definitions at {revision}: "
            f"expected={expected_columns!r} actual={column_definitions!r}"
        )

    normalized_foreign_keys = {
        name: (*definition[:9], normalize_sql(definition[9]))
        for name, definition in foreign_key_definitions.items()
    }
    normalized_expected_foreign_keys = {
        name: (*definition[:9], normalize_sql(definition[9]))
        for name, definition in expected_foreign_keys.items()
    }
    if normalized_foreign_keys != normalized_expected_foreign_keys:
        raise RuntimeError(
            f"Unexpected grade-override foreign key definitions at {revision}: "
            f"expected={normalized_expected_foreign_keys!r} "
            f"actual={normalized_foreign_keys!r}"
        )

    normalized_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in index_definitions.items()
    }
    normalized_expected_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in expected_indexes.items()
    }
    if normalized_indexes != normalized_expected_indexes:
        raise RuntimeError(
            f"Unexpected grade-override index definitions at {revision}: "
            f"expected={normalized_expected_indexes!r} "
            f"actual={normalized_indexes!r}"
        )


def soft_delete_foreign_key_definitions(
    cursor: PsycopgCursor,
) -> dict[
    str,
    tuple[
        str,
        tuple[str, ...],
        str,
        tuple[str, ...],
        str,
        str,
        bool,
        bool,
        bool,
        str,
    ],
]:
    cursor.execute(
        """
        SELECT
            pg_constraint.conname,
            source_class.relname,
            ARRAY(
                SELECT source_attribute.attname
                FROM unnest(pg_constraint.conkey)
                     WITH ORDINALITY AS source_key(attnum, position)
                JOIN pg_attribute AS source_attribute
                  ON source_attribute.attrelid = pg_constraint.conrelid
                 AND source_attribute.attnum = source_key.attnum
                ORDER BY source_key.position
            ),
            target_class.relname,
            ARRAY(
                SELECT target_attribute.attname
                FROM unnest(pg_constraint.confkey)
                     WITH ORDINALITY AS target_key(attnum, position)
                JOIN pg_attribute AS target_attribute
                  ON target_attribute.attrelid = pg_constraint.confrelid
                 AND target_attribute.attnum = target_key.attnum
                ORDER BY target_key.position
            ),
            pg_constraint.confdeltype,
            pg_constraint.confupdtype,
            pg_constraint.convalidated,
            pg_constraint.condeferrable,
            pg_constraint.condeferred,
            pg_get_constraintdef(pg_constraint.oid, true)
        FROM pg_constraint
        JOIN pg_class AS source_class
          ON source_class.oid = pg_constraint.conrelid
        JOIN pg_class AS target_class
          ON target_class.oid = pg_constraint.confrelid
        JOIN pg_namespace
          ON pg_namespace.oid = source_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND pg_constraint.contype = 'f'
          AND source_class.relname = ANY(%s)
          AND EXISTS (
              SELECT 1
              FROM unnest(pg_constraint.conkey) AS source_key(attnum)
              JOIN pg_attribute AS source_attribute
                ON source_attribute.attrelid = pg_constraint.conrelid
               AND source_attribute.attnum = source_key.attnum
              WHERE source_attribute.attname = 'deleted_by_id'
          )
        """,
        (list(SOFT_DELETE_TABLES),),
    )
    return {
        row[0]: (
            row[1],
            tuple(row[2]),
            row[3],
            tuple(row[4]),
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
        )
        for row in cursor.fetchall()
    }


def soft_delete_index_definitions(
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
          AND index_class.relname = ANY(%s)
        """,
        (list(EXPECTED_SOFT_DELETE_INDEX_DEFINITIONS),),
    )
    return {
        row[0]: (row[1], row[2], row[3], row[4], row[5], row[6])
        for row in cursor.fetchall()
    }


def normalize_sql(definition: str) -> str:
    return " ".join(definition.split())


def rag_embedding_type(cursor: PsycopgCursor) -> str | None:
    cursor.execute(
        """
        SELECT format_type(attribute.atttypid, attribute.atttypmod)
        FROM pg_attribute AS attribute
        JOIN pg_class AS table_class ON table_class.oid = attribute.attrelid
        JOIN pg_namespace ON pg_namespace.oid = table_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND table_class.relname = 'document_chunks'
          AND attribute.attname = 'embedding'
          AND NOT attribute.attisdropped
        """
    )
    row = cursor.fetchone()
    return row[0] if row else None


def rag_index_definitions(cursor: PsycopgCursor) -> dict[str, str]:
    cursor.execute(
        """
        SELECT index_class.relname, pg_get_indexdef(index_class.oid)
        FROM pg_index
        JOIN pg_class AS index_class ON index_class.oid = pg_index.indexrelid
        JOIN pg_namespace ON pg_namespace.oid = index_class.relnamespace
        WHERE pg_namespace.nspname = 'public'
          AND index_class.relname = ANY(%s)
        """,
        (list(EXPECTED_RAG_INDEX_FRAGMENTS),),
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


def validate_rag_schema_state(
    revision: str,
    *,
    embedding_type: str | None,
    index_definitions: dict[str, str],
) -> None:
    if revision == "head":
        if embedding_type != "vector(1536)":
            raise RuntimeError(
                "Unexpected document_chunks.embedding type at head: "
                f"expected='vector(1536)' actual={embedding_type!r}"
            )
        if set(index_definitions) != set(EXPECTED_RAG_INDEX_FRAGMENTS):
            raise RuntimeError(
                "Unexpected RAG indexes at head: "
                f"expected={sorted(EXPECTED_RAG_INDEX_FRAGMENTS)} "
                f"actual={sorted(index_definitions)}"
            )
        for name, fragments in EXPECTED_RAG_INDEX_FRAGMENTS.items():
            validate_definition_fragments(
                object_kind="RAG index",
                name=name,
                definition=index_definitions[name],
                expected_fragments=fragments,
            )
    elif revision == "base":
        if embedding_type is not None or index_definitions:
            raise RuntimeError(
                "RAG schema remains at base: "
                f"embedding_type={embedding_type!r} indexes={sorted(index_definitions)}"
            )
    else:
        raise RuntimeError(f"Unsupported RAG schema assertion revision: {revision}")


def assert_rag_previous_schema(manager: TestDatabaseManager) -> None:
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            embedding_type = rag_embedding_type(cursor)
            indexes = rag_index_definitions(cursor)
    finally:
        connection.close()
    if embedding_type != "vector(1536)" or indexes:
        raise RuntimeError(
            "Unexpected RAG schema before semantic migration: "
            f"embedding_type={embedding_type!r} indexes={sorted(indexes)}"
        )


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


def validate_ownership_schema_state(
    revision: str,
    *,
    column_definitions: dict[
        tuple[str, str], tuple[str, bool, str | None]
    ],
    foreign_key_definitions: dict[
        str,
        tuple[
            str,
            tuple[str, ...],
            str,
            tuple[str, ...],
            str,
            str,
            bool,
            bool,
            bool,
            str,
        ],
    ],
    index_definitions: dict[str, tuple[bool, bool, bool, bool, str, str]],
) -> None:
    expected_columns = (
        EXPECTED_OWNERSHIP_COLUMN_DEFINITIONS if revision == "head" else {}
    )
    expected_foreign_keys = (
        EXPECTED_OWNERSHIP_FOREIGN_KEY_DEFINITIONS
        if revision == "head"
        else {}
    )
    expected_indexes = (
        EXPECTED_OWNERSHIP_INDEX_DEFINITIONS if revision == "head" else {}
    )
    if column_definitions != expected_columns:
        raise RuntimeError(
            f"Unexpected ownership column definitions at {revision}: "
            f"expected={expected_columns!r} actual={column_definitions!r}"
        )

    normalized_foreign_keys = {
        name: (*definition[:9], normalize_sql(definition[9]))
        for name, definition in foreign_key_definitions.items()
    }
    normalized_expected_foreign_keys = {
        name: (*definition[:9], normalize_sql(definition[9]))
        for name, definition in expected_foreign_keys.items()
    }
    if normalized_foreign_keys != normalized_expected_foreign_keys:
        raise RuntimeError(
            f"Unexpected ownership foreign key definitions at {revision}: "
            f"expected={normalized_expected_foreign_keys!r} "
            f"actual={normalized_foreign_keys!r}"
        )

    normalized_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in index_definitions.items()
    }
    normalized_expected_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in expected_indexes.items()
    }
    if normalized_indexes != normalized_expected_indexes:
        raise RuntimeError(
            f"Unexpected ownership index definitions at {revision}: "
            f"expected={normalized_expected_indexes!r} "
            f"actual={normalized_indexes!r}"
        )


def validate_soft_delete_schema_state(
    revision: str,
    *,
    column_definitions: dict[
        tuple[str, str], tuple[str, bool, str | None]
    ],
    foreign_key_definitions: dict[
        str,
        tuple[
            str,
            tuple[str, ...],
            str,
            tuple[str, ...],
            str,
            str,
            bool,
            bool,
            bool,
            str,
        ],
    ],
    index_definitions: dict[str, tuple[bool, bool, bool, bool, str, str]],
) -> None:
    expected_columns = (
        EXPECTED_SOFT_DELETE_COLUMN_DEFINITIONS if revision == "head" else {}
    )
    expected_foreign_keys = (
        EXPECTED_SOFT_DELETE_FOREIGN_KEY_DEFINITIONS
        if revision == "head"
        else {}
    )
    expected_indexes = (
        EXPECTED_SOFT_DELETE_INDEX_DEFINITIONS if revision == "head" else {}
    )
    if column_definitions != expected_columns:
        raise RuntimeError(
            f"Unexpected soft-delete column definitions at {revision}: "
            f"expected={expected_columns!r} actual={column_definitions!r}"
        )

    normalized_foreign_keys = {
        name: (*definition[:9], normalize_sql(definition[9]))
        for name, definition in foreign_key_definitions.items()
    }
    normalized_expected_foreign_keys = {
        name: (*definition[:9], normalize_sql(definition[9]))
        for name, definition in expected_foreign_keys.items()
    }
    if normalized_foreign_keys != normalized_expected_foreign_keys:
        raise RuntimeError(
            f"Unexpected soft-delete foreign key definitions at {revision}: "
            f"expected={normalized_expected_foreign_keys!r} "
            f"actual={normalized_foreign_keys!r}"
        )

    normalized_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in index_definitions.items()
    }
    normalized_expected_indexes = {
        name: (*definition[:5], normalize_sql(definition[5]))
        for name, definition in expected_indexes.items()
    }
    if normalized_indexes != normalized_expected_indexes:
        raise RuntimeError(
            f"Unexpected soft-delete index definitions at {revision}: "
            f"expected={normalized_expected_indexes!r} "
            f"actual={normalized_indexes!r}"
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
            enum_labels = public_enum_labels(cursor)
            question_type_column = question_type_column_definition(cursor)
            audit_function = audit_function_exists(cursor)
            audit_triggers = audit_trigger_definitions(cursor)
            audit_columns = audit_column_definitions(cursor)
            audit_non_nullable_columns = audit_non_nullable_column_names(cursor)
            audit_indexes = audit_index_definitions(cursor)
            audit_constraints = audit_constraint_definitions(cursor)
            ownership_columns = ownership_column_definitions(cursor)
            ownership_foreign_keys = ownership_foreign_key_definitions(cursor)
            ownership_indexes = ownership_index_definitions(cursor)
            soft_delete_columns = soft_delete_column_definitions(cursor)
            soft_delete_foreign_keys = soft_delete_foreign_key_definitions(cursor)
            soft_delete_indexes = soft_delete_index_definitions(cursor)
            grade_override_columns = grade_override_column_definitions(cursor)
            grade_override_foreign_keys = grade_override_foreign_key_definitions(
                cursor
            )
            grade_override_indexes = grade_override_index_definitions(cursor)
            rag_embedding = rag_embedding_type(cursor)
            rag_indexes = rag_index_definitions(cursor)
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
    validate_question_type_schema_state(
        revision,
        enum_labels=enum_labels,
        column_definition=question_type_column,
    )
    validate_audit_schema_state(
        revision,
        column_definitions=audit_columns,
        non_nullable_columns=audit_non_nullable_columns,
        index_definitions=audit_indexes,
        constraint_definitions=audit_constraints,
    )
    validate_ownership_schema_state(
        revision,
        column_definitions=ownership_columns,
        foreign_key_definitions=ownership_foreign_keys,
        index_definitions=ownership_indexes,
    )
    validate_soft_delete_schema_state(
        revision,
        column_definitions=soft_delete_columns,
        foreign_key_definitions=soft_delete_foreign_keys,
        index_definitions=soft_delete_indexes,
    )
    validate_grade_override_schema_state(
        revision,
        column_definitions=grade_override_columns,
        foreign_key_definitions=grade_override_foreign_keys,
        index_definitions=grade_override_indexes,
    )
    validate_rag_schema_state(
        revision,
        embedding_type=rag_embedding,
        index_definitions=rag_indexes,
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
        f"audit_constraints={len(audit_constraints)} "
        f"ownership_columns={len(ownership_columns)} "
        f"ownership_foreign_keys={len(ownership_foreign_keys)} "
        f"ownership_indexes={len(ownership_indexes)} "
        f"soft_delete_columns={len(soft_delete_columns)} "
        f"soft_delete_foreign_keys={len(soft_delete_foreign_keys)} "
        f"soft_delete_indexes={len(soft_delete_indexes)} "
        f"grade_override_columns={len(grade_override_columns)} "
        f"grade_override_foreign_keys={len(grade_override_foreign_keys)} "
        f"grade_override_indexes={len(grade_override_indexes)}",
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


def seed_legacy_ownership_fixture(
    manager: TestDatabaseManager,
) -> tuple[uuid.UUID, uuid.UUID]:
    topic_id = uuid.uuid4()
    question_id = uuid.uuid4()
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            revisions = current_revisions(cursor)
            if revisions != {OWNERSHIP_PREVIOUS_REVISION}:
                raise RuntimeError(
                    "Legacy ownership fixture requires the previous head: "
                    f"expected={OWNERSHIP_PREVIOUS_REVISION} "
                    f"actual={sorted(revisions)}"
                )
            cursor.execute(
                "INSERT INTO topics (id, name) VALUES (%s, %s)",
                (str(topic_id), f"Legacy topic {topic_id}"),
            )
            cursor.execute(
                "INSERT INTO questions (id, content) VALUES (%s, %s)",
                (str(question_id), f"Legacy question {question_id}"),
            )
        connection.commit()
    finally:
        connection.close()

    print("MIGRATION_LEGACY_OWNERSHIP_FIXTURE_SEEDED", flush=True)
    return topic_id, question_id


def seed_pre_migration_question_types(
    manager: TestDatabaseManager,
) -> dict[str, uuid.UUID]:
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            if current_revisions(cursor) != {SINGLE_CHOICE_PREVIOUS_REVISION}:
                raise RuntimeError("Question fixture requires ca82f9a51d44")
            expected_labels = dict(EXPECTED_HEAD_ENUM_LABELS)
            expected_labels["questiontype"] = (
                "MULTIPLE_CHOICE",
                "MATCHING",
                "FILL_IN_BLANK",
            )
            if public_enum_labels(cursor) != expected_labels:
                raise RuntimeError("Pre-migration enum labels are not exact")
            question_ids = {
                label: uuid.uuid4()
                for label in (
                    "MULTIPLE_CHOICE",
                    "MATCHING",
                    "FILL_IN_BLANK",
                )
            }
            for label, question_id in question_ids.items():
                cursor.execute(
                    """
                    INSERT INTO questions (
                        id, content, question_type, difficulty,
                        is_ai_generated, points
                    )
                    VALUES (%s, %s, %s, 'EASY', false, 1)
                    """,
                    (
                        str(question_id),
                        f"Pre-migration preservation {label} {question_id}",
                        label,
                    ),
                )
        connection.commit()
    finally:
        connection.close()
    print("MIGRATION_PREEXISTING_QUESTION_TYPES_SEEDED", flush=True)
    return question_ids


def assert_question_types(
    manager: TestDatabaseManager,
    expected: dict[uuid.UUID, str],
) -> None:
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, question_type::text FROM questions "
                "WHERE id = ANY(%s::uuid[])",
                ([str(question_id) for question_id in expected],),
            )
            actual = {uuid.UUID(str(row[0])): row[1] for row in cursor.fetchall()}
    finally:
        connection.close()
    if actual != expected:
        raise RuntimeError(
            "Question rows were not preserved across enum migration: "
            f"expected={expected!r} actual={actual!r}"
        )


def assert_legacy_ownership_not_backfilled(
    manager: TestDatabaseManager,
    topic_id: uuid.UUID,
    question_id: uuid.UUID,
) -> None:
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT owner_id FROM topics WHERE id = %s",
                (str(topic_id),),
            )
            topic_row = cursor.fetchone()
            cursor.execute(
                "SELECT owner_id FROM questions WHERE id = %s",
                (str(question_id),),
            )
            question_row = cursor.fetchone()
    finally:
        connection.close()

    if topic_row != (None,) or question_row != (None,):
        raise RuntimeError(
            "Ownership migration unexpectedly backfilled legacy rows: "
            f"topic={topic_row!r} question={question_row!r}"
        )
    print("MIGRATION_LEGACY_OWNERSHIP_NULL_ASSERTION_PASSED", flush=True)


def assert_single_choice_downgrade_guard(
    manager: TestDatabaseManager,
    preserved_questions: dict[uuid.UUID, str],
) -> None:
    single_choice_id = uuid.uuid4()
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO questions ("
                "id, content, question_type, difficulty, is_ai_generated, points"
                ") VALUES (%s, %s, 'SINGLE_CHOICE', 'EASY', false, 1)",
                (
                    str(single_choice_id),
                    f"Downgrade guard {single_choice_id}",
                ),
            )
        connection.commit()
    finally:
        connection.close()

    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "downgrade",
            SINGLE_CHOICE_PREVIOUS_REVISION,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if rejected.returncode == 0:
        raise RuntimeError("Single-choice downgrade unexpectedly succeeded")

    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            if current_revisions(cursor) != {expected_head()}:
                raise RuntimeError("Rejected downgrade changed the Alembic revision")
            if public_enum_labels(cursor) != EXPECTED_HEAD_ENUM_LABELS:
                raise RuntimeError("Rejected downgrade changed enum labels")
            if question_type_column_definition(cursor) != EXPECTED_QUESTION_TYPE_COLUMN:
                raise RuntimeError("Rejected downgrade changed the question_type column")
            cursor.execute(
                "DELETE FROM questions WHERE id = ANY(%s::uuid[])",
                ([str(single_choice_id)],),
            )
        connection.commit()
    finally:
        connection.close()
    assert_question_types(
        manager,
        {**preserved_questions},
    )

    downgraded = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "downgrade",
            SINGLE_CHOICE_PREVIOUS_REVISION,
        ],
        check=False,
    )
    if downgraded.returncode != 0:
        raise RuntimeError("Clean single-choice downgrade failed")

    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            if current_revisions(cursor) != {SINGLE_CHOICE_PREVIOUS_REVISION}:
                raise RuntimeError("Clean downgrade reached the wrong revision")
            expected_previous_labels = dict(EXPECTED_HEAD_ENUM_LABELS)
            expected_previous_labels["questiontype"] = (
                "MULTIPLE_CHOICE",
                "MATCHING",
                "FILL_IN_BLANK",
            )
            if public_enum_labels(cursor) != expected_previous_labels:
                raise RuntimeError("Clean downgrade produced incorrect enum labels")
            if question_type_column_definition(cursor) != EXPECTED_QUESTION_TYPE_COLUMN:
                raise RuntimeError("Clean downgrade changed the column contract")
    finally:
        connection.close()
    assert_question_types(manager, preserved_questions)

    upgraded = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "upgrade",
            "head",
        ],
        check=False,
    )
    if upgraded.returncode != 0:
        raise RuntimeError("Re-upgrade after the enum downgrade failed")
    assert_schema_state(manager, "head")
    assert_question_types(manager, preserved_questions)
    print("MIGRATION_SINGLE_CHOICE_DOWNGRADE_GUARD_PASSED", flush=True)


def seed_soft_delete_downgrade_probe(manager: TestDatabaseManager) -> uuid.UUID:
    """Insert a soft-deleted topic so the downgrade-refusal path is real."""
    topic_id = uuid.uuid4()
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO topics (id, name, deleted_at) "
                "VALUES (%s, %s, now())",
                (str(topic_id), f"Soft-delete downgrade probe {topic_id}"),
            )
        connection.commit()
    finally:
        connection.close()
    print("MIGRATION_SOFT_DELETE_PROBE_SEEDED", flush=True)
    return topic_id


def assert_soft_delete_downgrade_guard(manager: TestDatabaseManager) -> None:
    probe_topic_id = seed_soft_delete_downgrade_probe(manager)

    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "downgrade",
            SOFT_DELETE_PREVIOUS_REVISION,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if rejected.returncode == 0:
        raise RuntimeError(
            "Soft-delete column downgrade unexpectedly succeeded while a "
            "deleted row exists"
        )

    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            if current_revisions(cursor) != {expected_head()}:
                raise RuntimeError(
                    "Rejected soft-delete downgrade changed the Alembic revision"
                )
            columns = soft_delete_column_definitions(cursor)
    finally:
        connection.close()
    if columns != EXPECTED_SOFT_DELETE_COLUMN_DEFINITIONS:
        raise RuntimeError(
            "Rejected soft-delete downgrade changed the soft-delete columns"
        )

    # Clear the probe so a clean downgrade can proceed.
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM topics WHERE id = %s", (str(probe_topic_id),)
            )
        connection.commit()
    finally:
        connection.close()

    downgraded = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "downgrade",
            SOFT_DELETE_PREVIOUS_REVISION,
        ],
        check=False,
    )
    if downgraded.returncode != 0:
        raise RuntimeError("Clean soft-delete downgrade failed")

    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            if current_revisions(cursor) != {SOFT_DELETE_PREVIOUS_REVISION}:
                raise RuntimeError(
                    "Clean soft-delete downgrade reached the wrong revision"
                )
            columns = soft_delete_column_definitions(cursor)
            if columns:
                raise RuntimeError(
                    "Clean soft-delete downgrade left columns behind: "
                    f"{columns!r}"
                )
    finally:
        connection.close()

    upgraded = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "upgrade",
            "head",
        ],
        check=False,
    )
    if upgraded.returncode != 0:
        raise RuntimeError("Re-upgrade after the soft-delete downgrade failed")
    assert_schema_state(manager, "head")
    print("MIGRATION_SOFT_DELETE_DOWNGRADE_GUARD_PASSED", flush=True)


def seed_grade_override_downgrade_probe(manager: TestDatabaseManager) -> uuid.UUID:
    """Insert a manually-corrected answer so the downgrade-refusal path is real.

    `submission_id`/`question_id` are nullable at the DB level, so a minimal
    orphan row -- no exam/topic/submission fixture chain required -- is
    enough to exercise the guard: it only cares whether `overridden_at` is
    set, not what the correction belongs to.
    """
    answer_id = uuid.uuid4()
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO submission_answers "
                "(id, override_reason, overridden_at) "
                "VALUES (%s, %s, now())",
                (str(answer_id), "Migration round-trip probe"),
            )
        connection.commit()
    finally:
        connection.close()
    print("MIGRATION_GRADE_OVERRIDE_PROBE_SEEDED", flush=True)
    return answer_id


def assert_grade_override_downgrade_guard(manager: TestDatabaseManager) -> None:
    probe_answer_id = seed_grade_override_downgrade_probe(manager)

    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "downgrade",
            GRADE_OVERRIDE_PREVIOUS_REVISION,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if rejected.returncode == 0:
        raise RuntimeError(
            "Grade-override-trail downgrade unexpectedly succeeded while a "
            "corrected answer exists"
        )

    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            if current_revisions(cursor) != {expected_head()}:
                raise RuntimeError(
                    "Rejected grade-override downgrade changed the Alembic "
                    "revision"
                )
            columns = grade_override_columns_present(cursor)
    finally:
        connection.close()
    if columns != frozenset(GRADE_OVERRIDE_COLUMNS):
        raise RuntimeError(
            "Rejected grade-override downgrade changed the trail columns: "
            f"{columns!r}"
        )

    # Clear the probe so a clean downgrade can proceed.
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM submission_answers WHERE id = %s",
                (str(probe_answer_id),),
            )
        connection.commit()
    finally:
        connection.close()

    downgraded = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "downgrade",
            GRADE_OVERRIDE_PREVIOUS_REVISION,
        ],
        check=False,
    )
    if downgraded.returncode != 0:
        raise RuntimeError("Clean grade-override downgrade failed")

    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            if current_revisions(cursor) != {GRADE_OVERRIDE_PREVIOUS_REVISION}:
                raise RuntimeError(
                    "Clean grade-override downgrade reached the wrong revision"
                )
            columns = grade_override_columns_present(cursor)
            if columns:
                raise RuntimeError(
                    "Clean grade-override downgrade left columns behind: "
                    f"{columns!r}"
                )
    finally:
        connection.close()

    upgraded = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "upgrade",
            "head",
        ],
        check=False,
    )
    if upgraded.returncode != 0:
        raise RuntimeError("Re-upgrade after the grade-override downgrade failed")
    assert_schema_state(manager, "head")
    print("MIGRATION_GRADE_OVERRIDE_DOWNGRADE_GUARD_PASSED", flush=True)


def main() -> int:
    manager = build_manager()
    manager.create()
    legacy_fixture_ids: tuple[uuid.UUID, uuid.UUID] | None = None
    pre_migration_question_ids: dict[str, uuid.UUID] | None = None
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
            if revision == OWNERSHIP_PREVIOUS_REVISION:
                legacy_fixture_ids = seed_legacy_ownership_fixture(manager)
                print(f"MIGRATION_STAGE_PASSED stage={stage_name}", flush=True)
                continue
            if revision == SINGLE_CHOICE_PREVIOUS_REVISION:
                pre_migration_question_ids = seed_pre_migration_question_types(
                    manager
                )
                print(f"MIGRATION_STAGE_PASSED stage={stage_name}", flush=True)
                continue
            if revision == RAG_PREVIOUS_REVISION:
                assert_rag_previous_schema(manager)
                print(f"MIGRATION_STAGE_PASSED stage={stage_name}", flush=True)
                continue
            assert_schema_state(manager, revision)
            assert_audit_append_only(manager, revision)
            if stage_name == "upgrade-head-1":
                if legacy_fixture_ids is None:
                    raise RuntimeError("Legacy ownership fixture was not seeded")
                if pre_migration_question_ids is None:
                    raise RuntimeError("Pre-migration question fixture was not seeded")
                assert_legacy_ownership_not_backfilled(
                    manager,
                    *legacy_fixture_ids,
                )
                expected_pre_migration_questions = {
                    question_id: label
                    for label, question_id in pre_migration_question_ids.items()
                }
                assert_question_types(
                    manager,
                    expected_pre_migration_questions,
                )
                assert_single_choice_downgrade_guard(
                    manager,
                    {
                        legacy_fixture_ids[1]: "MULTIPLE_CHOICE",
                        **expected_pre_migration_questions,
                    },
                )
                assert_soft_delete_downgrade_guard(manager)
                assert_grade_override_downgrade_guard(manager)
            print(f"MIGRATION_STAGE_PASSED stage={stage_name}", flush=True)
        return 0
    finally:
        manager.drop_created()


if __name__ == "__main__":
    raise SystemExit(main())
