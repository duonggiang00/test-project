import os
import subprocess
import sys


os.environ["ENV"] = "test"

from scripts.test_database import build_manager  # noqa: E402


def main() -> int:
    manager = build_manager()
    manager.create()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-m",
                "integration",
                "--junitxml=reports/integration.xml",
            ],
            check=False,
        )
        return completed.returncode
    finally:
        manager.drop_created()


if __name__ == "__main__":
    raise SystemExit(main())
