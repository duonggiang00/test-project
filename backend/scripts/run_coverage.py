import subprocess
import sys
from pathlib import Path


PYTEST_CACHE_ARGS = ["-p", "no:cacheprovider"]
REPORTS_DIRECTORY = Path("reports")


def run(arguments: list[str]) -> int:
    completed = subprocess.run([sys.executable, *arguments], check=False)
    return completed.returncode


def main() -> int:
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if run(["-m", "coverage", "erase"]) != 0:
        return 1

    unit_status = run(
        [
            "-m",
            "pytest",
            "-q",
            *PYTEST_CACHE_ARGS,
            "-m",
            "unit or contract",
            "--cov=app",
            "--cov-report=",
            "--junitxml=reports/coverage-fast.xml",
        ]
    )
    if unit_status != 0:
        return unit_status

    return run(
        [
            "-m",
            "scripts.run_integration",
            "--",
            "-q",
            *PYTEST_CACHE_ARGS,
            "-m",
            "integration",
            "--cov=app",
            "--cov-append",
            "--cov-report=json:reports/coverage.json",
            "--cov-report=term",
            "--junitxml=reports/coverage-integration.xml",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
