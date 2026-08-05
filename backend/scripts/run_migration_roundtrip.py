import os
import subprocess
import sys


os.environ["ENV"] = "test"

from scripts.test_database import build_manager  # noqa: E402


MIGRATION_STAGES = (
    ("upgrade-head-1", "upgrade", "head"),
    ("downgrade-base", "downgrade", "base"),
    ("upgrade-head-2", "upgrade", "head"),
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
            print(f"MIGRATION_STAGE_PASSED stage={stage_name}", flush=True)
        return 0
    finally:
        manager.drop_created()


if __name__ == "__main__":
    raise SystemExit(main())
