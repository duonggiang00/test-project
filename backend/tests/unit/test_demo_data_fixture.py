from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.demo_data.fixture import (
    DEFAULT_FIXTURE_ROOT,
    compute_content_hash,
    load_demo_fixture,
    stable_uuid,
)
from app.demo_data.loader import DemoDataError, validate_demo_database_target


def _copy_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "fixture"
    shutil.copytree(DEFAULT_FIXTURE_ROOT, target)
    return target


def _rewrite_json(root: Path, name: str, transform) -> None:
    path = root / name
    value = json.loads(path.read_text(encoding="utf-8"))
    transform(value)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["content_sha256"] = compute_content_hash(root, manifest["content_files"])
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


@pytest.mark.unit
def test_standard_fixture_has_required_inventory() -> None:
    fixture = load_demo_fixture()

    assert len(fixture.topics) == 9
    assert len(fixture.materials) == 6
    assert len(fixture.questions) == 60
    assert len(fixture.exams) == 6
    assert sum(len(deck.cards) for deck in fixture.flashcards) == 48
    assert sum(item.status == "submitted" for item in fixture.submissions) == 12
    assert sum(item.status == "in_progress" for item in fixture.submissions) == 3


@pytest.mark.unit
def test_stable_uuid_is_deterministic_and_entity_scoped() -> None:
    namespace = "playstudy/demo-standard-v1"

    assert stable_uuid(namespace, "topic", "math") == stable_uuid(namespace, "topic", "math")
    assert stable_uuid(namespace, "topic", "math") != stable_uuid(namespace, "exam", "math")


@pytest.mark.unit
def test_content_hash_detects_changed_fixture_file(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    (root / "topics.json").write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="content hash"):
        load_demo_fixture(root)


@pytest.mark.unit
def test_duplicate_key_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _rewrite_json(root, "topics.json", lambda rows: rows.append(dict(rows[0])))

    with pytest.raises(ValueError, match="duplicate topic keys"):
        load_demo_fixture(root)


@pytest.mark.unit
def test_missing_teacher_owner_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["teacher_email"] = ""
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="teacher_email"):
        load_demo_fixture(root)


@pytest.mark.unit
def test_missing_foreign_key_reference_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _rewrite_json(root, "materials.json", lambda rows: rows[0].update(topic="missing-topic"))

    with pytest.raises(ValueError, match="references missing topic"):
        load_demo_fixture(root)


@pytest.mark.unit
def test_single_choice_without_correct_option_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)

    def remove_correct(rows) -> None:
        for option in rows[0]["options"]:
            option["is_correct"] = False

    _rewrite_json(root, "questions.json", remove_correct)

    with pytest.raises(ValueError, match="exactly one correct option"):
        load_demo_fixture(root)


@pytest.mark.unit
def test_invalid_fill_in_blank_answer_contract_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)

    def remove_answers(rows) -> None:
        target = next(row for row in rows if row["question_type"] == "FILL_IN_BLANK")
        target["metadata"]["blanks"][0]["acceptable_answers"] = []

    _rewrite_json(root, "questions.json", remove_answers)

    with pytest.raises(ValueError, match="acceptable answers"):
        load_demo_fixture(root)


@pytest.mark.unit
def test_cross_subject_exam_question_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)

    def cross_subject(rows) -> None:
        target = next(row for row in rows if row["key"] == "math-published")
        target["questions"][0] = "python-foundations-q05"

    _rewrite_json(root, "exams.json", cross_subject)

    with pytest.raises(ValueError, match="another subject"):
        load_demo_fixture(root)


@pytest.mark.unit
def test_missing_material_file_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    (root / "materials" / "math_limits.txt").unlink()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["content_files"].remove("materials/math_limits.txt")
    manifest["content_sha256"] = compute_content_hash(root, manifest["content_files"])
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source file is missing"):
        load_demo_fixture(root)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("database_url", "environment"),
    [
        ("sqlite:///demo.db", "development"),
        ("postgresql://user:secret@db.example.com/demo_test", "test"),
        ("postgresql://user:secret@localhost/demo", "production"),
        ("postgresql://user:secret@localhost/demo", "test"),
    ],
)
def test_database_guard_rejects_unsafe_targets(database_url: str, environment: str) -> None:
    with pytest.raises(DemoDataError):
        validate_demo_database_target(database_url, environment)


@pytest.mark.unit
def test_database_guard_accepts_local_development_and_test() -> None:
    validate_demo_database_target("postgresql://user:secret@localhost/demo", "development")
    validate_demo_database_target("postgresql://user:secret@localhost/demo_test", "test")
