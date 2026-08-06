import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_migration_roundtrip as migration_runner


BACKEND_ROOT = Path(__file__).resolve().parents[2]


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
    )
    migration_runner.validate_schema_state(
        "base",
        head="head-revision",
        revisions=set(),
        tables=set(migration_runner.EXPECTED_BASE_TABLES),
        enums=set(migration_runner.EXPECTED_BASE_ENUMS),
    )


def test_rejects_mismatched_head_revision():
    with pytest.raises(RuntimeError, match="Expected Alembic head"):
        migration_runner.validate_schema_state(
            "head",
            head="expected-head",
            revisions={"unexpected-head"},
            tables=set(migration_runner.EXPECTED_HEAD_TABLES),
            enums=set(migration_runner.EXPECTED_HEAD_ENUMS),
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
