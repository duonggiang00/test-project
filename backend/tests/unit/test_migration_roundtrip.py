import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_migration_roundtrip as migration_runner


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def exact_audit_trigger_definitions():
    return {
        name: " ".join(fragments)
        for name, fragments in (
            migration_runner.EXPECTED_AUDIT_TRIGGER_FRAGMENTS.items()
        )
    }


def exact_audit_constraint_definitions():
    return dict(migration_runner.EXPECTED_AUDIT_CONSTRAINT_DEFINITIONS)


def exact_audit_index_definitions():
    return dict(migration_runner.EXPECTED_AUDIT_INDEX_DEFINITIONS)


def test_import_does_not_mutate_existing_environment_mode():
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os; "
                "os.environ['ENV'] = 'sentinel'; "
                "import scripts.run_migration_roundtrip; "
                "print(os.environ['ENV'])"
            ),
        ],
        cwd=BACKEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "sentinel"


def test_accepts_exact_head_and_base_schema_states():
    migration_runner.validate_schema_state(
        "head",
        head="head-revision",
        revisions={"head-revision"},
        tables=set(migration_runner.EXPECTED_HEAD_TABLES),
        enums=set(migration_runner.EXPECTED_HEAD_ENUMS),
        audit_function=True,
        audit_triggers=exact_audit_trigger_definitions(),
    )
    migration_runner.validate_schema_state(
        "base",
        head="head-revision",
        revisions=set(),
        tables=set(migration_runner.EXPECTED_BASE_TABLES),
        enums=set(migration_runner.EXPECTED_BASE_ENUMS),
        audit_function=False,
        audit_triggers={},
    )


def test_rejects_mismatched_head_revision():
    with pytest.raises(RuntimeError, match="Expected Alembic head"):
        migration_runner.validate_schema_state(
            "head",
            head="expected-head",
            revisions={"unexpected-head"},
            tables=set(migration_runner.EXPECTED_HEAD_TABLES),
            enums=set(migration_runner.EXPECTED_HEAD_ENUMS),
            audit_function=True,
            audit_triggers=exact_audit_trigger_definitions(),
        )


@pytest.mark.parametrize(
    ("tables", "enums", "message"),
    [
        (set(), {"role"}, "Unexpected public tables"),
        ({"user"}, set(), "Unexpected public enums"),
        ({"user", "users"}, {"role"}, "Unexpected public tables"),
        ({"user"}, {"role", "questiontype"}, "Unexpected public enums"),
    ],
)
def test_rejects_missing_or_stray_base_schema_objects(tables, enums, message):
    with pytest.raises(RuntimeError, match=message):
        migration_runner.validate_schema_state(
            "base",
            head="head-revision",
            revisions=set(),
            tables=tables,
            enums=enums,
            audit_function=False,
            audit_triggers={},
        )


@pytest.mark.parametrize(
    ("audit_function", "audit_triggers", "message"),
    [
        (False, exact_audit_trigger_definitions(), "mutation function"),
        (
            True,
            {
                migration_runner.AUDIT_MUTATION_TRIGGER: (
                    exact_audit_trigger_definitions()[
                        migration_runner.AUDIT_MUTATION_TRIGGER
                    ]
                )
            },
            "mutation triggers",
        ),
        (
            True,
            {
                migration_runner.AUDIT_TRUNCATE_TRIGGER: (
                    exact_audit_trigger_definitions()[
                        migration_runner.AUDIT_TRUNCATE_TRIGGER
                    ]
                )
            },
            "mutation triggers",
        ),
    ],
)
def test_rejects_missing_append_only_database_objects(
    audit_function,
    audit_triggers,
    message,
):
    with pytest.raises(RuntimeError, match=message):
        migration_runner.validate_schema_state(
            "head",
            head="head-revision",
            revisions={"head-revision"},
            tables=set(migration_runner.EXPECTED_HEAD_TABLES),
            enums=set(migration_runner.EXPECTED_HEAD_ENUMS),
            audit_function=audit_function,
            audit_triggers=audit_triggers,
        )


def test_rejects_incorrect_append_only_trigger_definition():
    trigger_definitions = exact_audit_trigger_definitions()
    trigger_definitions[migration_runner.AUDIT_TRUNCATE_TRIGGER] = (
        "CREATE TRIGGER trg_audit_events_no_truncate BEFORE TRUNCATE "
        "ON audit_events FOR EACH ROW EXECUTE FUNCTION "
        "prevent_audit_event_mutation()"
    )

    with pytest.raises(RuntimeError, match="trigger definition"):
        migration_runner.validate_schema_state(
            "head",
            head="head-revision",
            revisions={"head-revision"},
            tables=set(migration_runner.EXPECTED_HEAD_TABLES),
            enums=set(migration_runner.EXPECTED_HEAD_ENUMS),
            audit_function=True,
            audit_triggers=trigger_definitions,
        )


def test_accepts_exact_audit_schema_at_head_and_absence_at_base():
    migration_runner.validate_audit_schema_state(
        "head",
        column_definitions=dict(
            migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
        ),
        non_nullable_columns=set(
            migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
        ),
        index_definitions=exact_audit_index_definitions(),
        constraint_definitions=exact_audit_constraint_definitions(),
    )
    migration_runner.validate_audit_schema_state(
        "base",
        column_definitions={},
        non_nullable_columns=set(),
        index_definitions={},
        constraint_definitions={},
    )


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("non_nullable_columns", "non-null columns"),
        ("index_definitions", "audit index definitions"),
    ],
)
def test_rejects_incomplete_audit_schema(field, message):
    values = {
        "column_definitions": dict(
            migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
        ),
        "non_nullable_columns": set(
            migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
        ),
        "index_definitions": exact_audit_index_definitions(),
        "constraint_definitions": exact_audit_constraint_definitions(),
    }
    target = values[field]
    if isinstance(target, dict):
        target.pop(next(iter(target)))
    else:
        target.pop()

    with pytest.raises(RuntimeError, match=message):
        migration_runner.validate_audit_schema_state("head", **values)


@pytest.mark.parametrize(
    ("column", "unexpected_definition"),
    [
        ("request_id", ("character varying(63)", None)),
        ("occurred_at", ("timestamp without time zone", "now()")),
        ("changes", ("jsonb", None)),
    ],
)
def test_rejects_incorrect_audit_column_contract(
    column,
    unexpected_definition,
):
    column_definitions = dict(
        migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
    )
    column_definitions[column] = unexpected_definition

    with pytest.raises(RuntimeError, match="column definitions"):
        migration_runner.validate_audit_schema_state(
            "head",
            column_definitions=column_definitions,
            non_nullable_columns=set(
                migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
            ),
            index_definitions=exact_audit_index_definitions(),
            constraint_definitions=exact_audit_constraint_definitions(),
        )


def test_rejects_incomplete_audit_constraint_set():
    constraint_definitions = exact_audit_constraint_definitions()
    constraint_definitions.pop("ck_audit_events_actor_identity")

    with pytest.raises(RuntimeError, match="constraint definitions"):
        migration_runner.validate_audit_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
            ),
            non_nullable_columns=set(
                migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
            ),
            index_definitions=exact_audit_index_definitions(),
            constraint_definitions=constraint_definitions,
        )

    constraint_definitions = exact_audit_constraint_definitions()
    properties = constraint_definitions["ck_audit_events_action_format"][:4]
    constraint_definitions["ck_audit_events_action_format"] = (
        *properties,
        "CHECK (action IS NOT NULL)",
    )

    with pytest.raises(RuntimeError, match="constraint definitions"):
        migration_runner.validate_audit_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
            ),
            non_nullable_columns=set(
                migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
            ),
            index_definitions=exact_audit_index_definitions(),
            constraint_definitions=constraint_definitions,
        )


def test_rejects_incorrect_audit_constraint_properties_and_definition():
    constraint_definitions = exact_audit_constraint_definitions()
    _, validated, deferrable, deferred, definition = constraint_definitions[
        "audit_events_pkey"
    ]
    constraint_definitions["audit_events_pkey"] = (
        "c",
        validated,
        deferrable,
        deferred,
        definition,
    )

    with pytest.raises(RuntimeError, match="constraint definitions"):
        migration_runner.validate_audit_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
            ),
            non_nullable_columns=set(
                migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
            ),
            index_definitions=exact_audit_index_definitions(),
            constraint_definitions=constraint_definitions,
        )


@pytest.mark.parametrize(
    ("index_name", "unexpected_definition"),
    [
        (
            "ix_audit_events_entity",
            (
                False,
                False,
                True,
                True,
                "btree",
                "CREATE INDEX ix_audit_events_entity ON "
                "public.audit_events USING btree (entity_id, entity_type, "
                "occurred_at)",
            ),
        ),
        (
            "ix_audit_events_request_id",
            (
                True,
                False,
                True,
                True,
                "btree",
                "CREATE UNIQUE INDEX ix_audit_events_request_id ON "
                "public.audit_events USING btree (request_id)",
            ),
        ),
        (
            "ix_audit_events_entity",
            (
                False,
                False,
                True,
                True,
                "btree",
                "CREATE INDEX ix_audit_events_entity ON "
                "public.audit_events USING btree (entity_type, actor_id, "
                "occurred_at)",
            ),
        ),
    ],
)
def test_rejects_incorrect_audit_index_definition(
    index_name,
    unexpected_definition,
):
    index_definitions = exact_audit_index_definitions()
    index_definitions[index_name] = unexpected_definition

    with pytest.raises(RuntimeError, match="audit index definitions"):
        migration_runner.validate_audit_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
            ),
            non_nullable_columns=set(
                migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
            ),
            index_definitions=index_definitions,
            constraint_definitions=exact_audit_constraint_definitions(),
        )


def test_rejects_weakened_audit_check_constraint():
    constraint_definitions = exact_audit_constraint_definitions()
    properties = constraint_definitions["ck_audit_events_actor_role"][:4]
    constraint_definitions["ck_audit_events_actor_role"] = (
        *properties,
        "CHECK (TRUE OR actor_role::text = ANY (ARRAY["
        "'admin'::character varying, 'teacher'::character varying, "
        "'student'::character varying, 'system'::character varying]::text[]))",
    )

    with pytest.raises(RuntimeError, match="audit constraint definitions"):
        migration_runner.validate_audit_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
            ),
            non_nullable_columns=set(
                migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
            ),
            index_definitions=exact_audit_index_definitions(),
            constraint_definitions=constraint_definitions,
        )


def test_rejects_case_changed_audit_check_literal():
    constraint_definitions = exact_audit_constraint_definitions()
    properties = constraint_definitions["ck_audit_events_actor_role"][:4]
    definition = constraint_definitions["ck_audit_events_actor_role"][4]
    constraint_definitions["ck_audit_events_actor_role"] = (
        *properties,
        definition.replace("'admin'", "'ADMIN'"),
    )

    with pytest.raises(RuntimeError, match="audit constraint definitions"):
        migration_runner.validate_audit_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_AUDIT_COLUMN_DEFINITIONS
            ),
            non_nullable_columns=set(
                migration_runner.EXPECTED_AUDIT_NON_NULL_COLUMNS
            ),
            index_definitions=exact_audit_index_definitions(),
            constraint_definitions=constraint_definitions,
        )


def test_rejects_multiple_or_signature_mismatched_heads():
    with pytest.raises(RuntimeError, match="exactly one Alembic head"):
        migration_runner.validate_expected_head(
            {"head-a", "head-b"},
            {"head-a", "head-b"},
        )

    with pytest.raises(RuntimeError, match="graph and database model signature disagree"):
        migration_runner.validate_expected_head({"head-a"}, {"head-b"})


def test_cleanup_runs_when_schema_assertion_fails(monkeypatch):
    class FakeManager:
        created = False
        dropped = False

        def create(self):
            self.created = True

        def drop_created(self):
            self.dropped = True

    manager = FakeManager()
    monkeypatch.setattr(migration_runner, "build_manager", lambda: manager)
    monkeypatch.setattr(
        migration_runner.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=0),
    )

    def fail_assertion(*args, **kwargs):
        raise RuntimeError("schema mismatch")

    monkeypatch.setattr(migration_runner, "assert_schema_state", fail_assertion)

    with pytest.raises(RuntimeError, match="schema mismatch"):
        migration_runner.main()

    assert manager.created is True
    assert manager.dropped is True
