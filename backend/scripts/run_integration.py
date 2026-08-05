import os
import subprocess
import sys


os.environ["ENV"] = "test"

from scripts.test_database import build_manager  # noqa: E402


def main() -> int:
    extra_pytest_args = sys.argv[1:]
    if extra_pytest_args[:1] == ["--"]:
        extra_pytest_args = extra_pytest_args[1:]
    pytest_args = extra_pytest_args or [
        "-q",
        "-m",
        "integration",
        "--junitxml=reports/integration.xml",
    ]

    manager = build_manager()
    manager.create()
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", *pytest_args],
            check=False,
        )
        return completed.returncode
    finally:
        manager.drop_created()


if __name__ == "__main__":
    raise SystemExit(main())
