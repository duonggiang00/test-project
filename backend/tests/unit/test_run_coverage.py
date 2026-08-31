from pathlib import Path

import pytest

from scripts import run_coverage as coverage_runner


def test_main_creates_reports_and_disables_pytest_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    calls: list[list[str]] = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        coverage_runner,
        "run",
        lambda arguments: calls.append(arguments) or 0,
    )

    assert coverage_runner.main() == 0
    assert (tmp_path / "reports").is_dir()
    assert calls[0] == ["-m", "coverage", "erase"]
    assert calls[1][:5] == [
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    assert calls[2][:6] == [
        "-m",
        "scripts.run_integration",
        "--",
        "-q",
        "-p",
        "no:cacheprovider",
    ]


@pytest.mark.parametrize(
    ("statuses", "expected_status", "expected_calls"),
    [
        ([7], 1, 1),
        ([0, 9], 9, 2),
        ([0, 0, 11], 11, 3),
    ],
)
def test_main_propagates_phase_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    statuses: list[int],
    expected_status: int,
    expected_calls: int,
):
    calls: list[list[str]] = []
    pending_statuses = iter(statuses)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        coverage_runner,
        "run",
        lambda arguments: calls.append(arguments) or next(pending_statuses),
    )

    assert coverage_runner.main() == expected_status
    assert len(calls) == expected_calls
