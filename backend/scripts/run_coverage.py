import subprocess
import sys


def run(arguments: list[str]) -> int:
    completed = subprocess.run([sys.executable, *arguments], check=False)
    return completed.returncode


def main() -> int:
    if run(["-m", "coverage", "erase"]) != 0:
        return 1

    unit_status = run(
        [
            "-m",
            "pytest",
            "-q",
            "-m",
            "unit",
            "--cov=app",
            "--cov-report=",
            "--junitxml=reports/coverage-unit.xml",
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
