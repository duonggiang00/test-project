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


def exact_ownership_foreign_key_definitions():
    return dict(migration_runner.EXPECTED_OWNERSHIP_FOREIGN_KEY_DEFINITIONS)


def exact_ownership_index_definitions():
    return dict(migration_runner.EXPECTED_OWNERSHIP_INDEX_DEFINITIONS)


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


def test_accepts_exact_question_type_schema_at_head_and_base():
    migration_runner.validate_question_type_schema_state(
        "head",
        enum_labels=dict(migration_runner.EXPECTED_HEAD_ENUM_LABELS),
        column_definition=migration_runner.EXPECTED_QUESTION_TYPE_COLUMN,
    )
    migration_runner.validate_question_type_schema_state(
        "base",
        enum_labels=dict(migration_runner.EXPECTED_BASE_ENUM_LABELS),
        column_definition=None,
    )


@pytest.mark.parametrize(
    "unexpected_labels",
    [
        ("MULTIPLE_CHOICE", "MATCHING", "FILL_IN_BLANK"),
        (
            "MULTIPLE_CHOICE",
            "SINGLE_CHOICE",
            "MATCHING",
            "FILL_IN_BLANK",
        ),
        (
            "SINGLE_CHOICE",
            "MULTIPLE_CHOICE",
            "MATCHING",
            "FILL_IN_BLANK",
            "TRUE_FALSE",
        ),
    ],
)
def test_rejects_missing_reordered_or_stray_question_type_labels(
    unexpected_labels,
):
    labels = dict(migration_runner.EXPECTED_HEAD_ENUM_LABELS)
    labels["questiontype"] = unexpected_labels

    with pytest.raises(RuntimeError, match="enum labels"):
        migration_runner.validate_question_type_schema_state(
            "head",
            enum_labels=labels,
            column_definition=migration_runner.EXPECTED_QUESTION_TYPE_COLUMN,
        )


@pytest.mark.parametrize(
    "unexpected_column",
    [
        ("character varying", "varchar", False, "'MULTIPLE_CHOICE'::text"),
        ("USER-DEFINED", "questiontype", True, "'MULTIPLE_CHOICE'::questiontype"),
        ("USER-DEFINED", "questiontype", False, None),
    ],
)
def test_rejects_incorrect_question_type_column_contract(unexpected_column):
    with pytest.raises(RuntimeError, match="column definition"):
        migration_runner.validate_question_type_schema_state(
            "head",
            enum_labels=dict(migration_runner.EXPECTED_HEAD_ENUM_LABELS),
            column_definition=unexpected_column,
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


def test_accepts_exact_ownership_schema_at_head_and_absence_at_base():
    migration_runner.validate_ownership_schema_state(
        "head",
        column_definitions=dict(
            migration_runner.EXPECTED_OWNERSHIP_COLUMN_DEFINITIONS
        ),
        foreign_key_definitions=exact_ownership_foreign_key_definitions(),
        index_definitions=exact_ownership_index_definitions(),
    )
    migration_runner.validate_ownership_schema_state(
        "base",
        column_definitions={},
        foreign_key_definitions={},
        index_definitions={},
    )


@pytest.mark.parametrize(
    "unexpected_definition",
    [
        ("character varying(36)", True, None),
        ("uuid", False, None),
        ("uuid", True, "gen_random_uuid()"),
    ],
)
def test_rejects_incorrect_ownership_column_definition(
    unexpected_definition,
):
    columns = dict(migration_runner.EXPECTED_OWNERSHIP_COLUMN_DEFINITIONS)
    columns[("topics", "owner_id")] = unexpected_definition

    with pytest.raises(RuntimeError, match="ownership column definitions"):
        migration_runner.validate_ownership_schema_state(
            "head",
            column_definitions=columns,
            foreign_key_definitions=(
                exact_ownership_foreign_key_definitions()
            ),
            index_definitions=exact_ownership_index_definitions(),
        )


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    [
        ("name", "ownership foreign key definitions"),
        ("target", "ownership foreign key definitions"),
        ("delete", "ownership foreign key definitions"),
    ],
)
def test_rejects_incorrect_ownership_foreign_key(
    mutation,
    expected_message,
):
    foreign_keys = exact_ownership_foreign_key_definitions()
    definition = foreign_keys["topics_owner_id_fkey"]
    if mutation == "name":
        foreign_keys["unexpected_topics_owner_fkey"] = foreign_keys.pop(
            "topics_owner_id_fkey"
        )
    elif mutation == "target":
        foreign_keys["topics_owner_id_fkey"] = (
            *definition[:2],
            "topics",
            *definition[3:],
        )
    else:
        foreign_keys["topics_owner_id_fkey"] = (
            *definition[:4],
            "c",
            *definition[5:9],
            "FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE",
        )

    with pytest.raises(RuntimeError, match=expected_message):
        migration_runner.validate_ownership_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_OWNERSHIP_COLUMN_DEFINITIONS
            ),
            foreign_key_definitions=foreign_keys,
            index_definitions=exact_ownership_index_definitions(),
        )


@pytest.mark.parametrize("mutation", ["missing", "unique", "method", "column"])
def test_rejects_incorrect_ownership_index(mutation):
    indexes = exact_ownership_index_definitions()
    name = "ix_topics_owner_id"
    definition = indexes[name]
    if mutation == "missing":
        indexes.pop(name)
    elif mutation == "unique":
        indexes[name] = (True, *definition[1:])
    elif mutation == "method":
        indexes[name] = (*definition[:4], "hash", definition[5])
    else:
        indexes[name] = (
            *definition[:5],
            definition[5].replace("(owner_id)", "(parent_id)"),
        )

    with pytest.raises(RuntimeError, match="ownership index definitions"):
        migration_runner.validate_ownership_schema_state(
            "head",
            column_definitions=dict(
                migration_runner.EXPECTED_OWNERSHIP_COLUMN_DEFINITIONS
            ),
            foreign_key_definitions=(
                exact_ownership_foreign_key_definitions()
            ),
            index_definitions=indexes,
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
    monkeypatch.setattr(
        migration_runner,
        "seed_legacy_ownership_fixture",
        lambda _manager: (None, None),
    )
    monkeypatch.setattr(
        migration_runner,
        "seed_pre_migration_question_types",
        lambda _manager: {},
    )

    def fail_assertion(*args, **kwargs):
        raise RuntimeError("schema mismatch")

    monkeypatch.setattr(migration_runner, "assert_schema_state", fail_assertion)

    with pytest.raises(RuntimeError, match="schema mismatch"):
        migration_runner.main()

    assert manager.created is True
    assert manager.dropped is True
