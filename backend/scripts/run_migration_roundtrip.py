from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg2.extensions import cursor as PsycopgCursor

if TYPE_CHECKING:
    from scripts.test_database import TestDatabaseManager


MIGRATION_STAGES = (
    ("upgrade-head-1", "upgrade", "head"),
    ("downgrade-base", "downgrade", "base"),
    ("upgrade-head-2", "upgrade", "head"),
)

EXPECTED_HEAD_TABLES = {
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


def validate_schema_state(
    revision: str,
    *,
    head: str,
    revisions: set[str],
    tables: set[str],
    enums: set[str],
) -> None:
    if revision == "head":
        if revisions != {head}:
            raise RuntimeError(
                f"Expected Alembic head {head}, got {sorted(revisions)}"
            )
        expected_tables = EXPECTED_HEAD_TABLES
        expected_enums = EXPECTED_HEAD_ENUMS
    elif revision == "base":
        if revisions:
            raise RuntimeError(
                f"Expected no Alembic revision at base, got {sorted(revisions)}"
            )
        expected_tables = EXPECTED_BASE_TABLES
        expected_enums = EXPECTED_BASE_ENUMS
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


def assert_schema_state(manager: TestDatabaseManager, revision: str) -> None:
    head = expected_head()
    connection = manager.connect_target()
    try:
        with connection.cursor() as cursor:
            revisions = current_revisions(cursor)
            tables = public_table_names(cursor)
            enums = public_enum_names(cursor)
    finally:
        connection.close()

    validate_schema_state(
        revision,
        head=head,
        revisions=revisions,
        tables=tables,
        enums=enums,
    )

    print(
        "MIGRATION_SCHEMA_ASSERTIONS_PASSED "
        f"revision={revision} revisions={','.join(sorted(revisions)) or 'base'} "
        f"tables={len(tables)} enums={','.join(sorted(enums))}",
        flush=True,
    )


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
            print(f"MIGRATION_STAGE_PASSED stage={stage_name}", flush=True)
        return 0
    finally:
        manager.drop_created()


if __name__ == "__main__":
    raise SystemExit(main())
