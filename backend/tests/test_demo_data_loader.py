from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import delete, select, text

from app.core.file_storage import LocalFileStorage
from app.core.security import create_access_token, get_password_hash
from app.demo_data.fixture import load_demo_fixture, stable_uuid
from app.demo_data.loader import DemoDataError, DemoDataManager
from app.models.flashcard import FlashcardProgress
from app.models.submission import Submission
from app.models.topic import Topic
from app.models.user import User


def _current_repository_head() -> str:
    """The real head, computed the same way `_assert_revision` does.

    Hardcoding a revision literal here is exactly what made the fixture's
    old exact-pin manifest field go stale (DATA-DEMO-002): it was still
    `f9f952e6df1a` three heads after that stopped being true. Computing it
    live means this fixture can never go stale the same way again.
    """
    backend_root = Path(__file__).resolve().parents[1]
    script = ScriptDirectory.from_config(
        AlembicConfig(str(backend_root / "alembic.ini"))
    )
    heads = script.get_heads()
    assert len(heads) == 1, f"expected a single Alembic head, got {heads!r}"
    return heads[0]


@pytest.fixture(scope="module")
def demo_accounts(db):
    db.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
    db.execute(text("DELETE FROM alembic_version"))
    db.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:head)"),
        {"head": _current_repository_head()},
    )
    accounts = {}
    for role, email, name in [
        ("teacher", "other.teacher@example.invalid", "Other Teacher"),
        ("student", "api.student@example.invalid", "API Student"),
    ]:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                id=uuid4(),
                email=email,
                password_hash=get_password_hash("integration-only-password"),
                full_name=name,
                role=role,
            )
            db.add(user)
            db.flush()
        accounts[email] = user
    db.commit()
    return accounts


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.mark.integration
def test_demo_dataset_lifecycle_and_api_contracts(client, db, demo_accounts) -> None:
    fixture = load_demo_fixture()
    storage = LocalFileStorage(Path("uploads"), namespace=fixture.manifest.dataset_id)
    manager = DemoDataManager(
        fixture,
        db,
        storage,
        database_url="postgresql://test:test@localhost/playstudy_test",
        environment="test",
    )
    other_teacher = demo_accounts["other.teacher@example.invalid"]
    api_student = demo_accounts["api.student@example.invalid"]

    initial_plan = manager.plan()
    assert all(item.create > 0 for item in initial_plan.items)

    applied = manager.apply()
    teacher = db.scalar(select(User).where(User.email == "teacher@example.com"))
    admin = db.scalar(select(User).where(User.email == "admin@example.com"))
    student = db.scalar(select(User).where(User.email == "student@example.com"))
    assert teacher is not None
    assert admin is not None
    assert student is not None
    unrelated_topic = Topic(
        id=uuid4(),
        owner_id=teacher.id,
        name="Unrelated integration topic",
        description="Must survive dataset reset.",
    )
    db.add(unrelated_topic)
    db.commit()
    assert applied.counts["topics"] == 9
    assert applied.counts["questions"] == 60
    assert applied.counts["submission_answers"] == 120
    assert applied.total_score_min == 20.0
    assert applied.total_score_max == 100.0

    reapplied = manager.apply()
    assert reapplied.counts == applied.counts
    assert all(item.create == 0 for item in manager.plan().items)
    math_topic_id = stable_uuid(fixture.manifest.namespace, "topic", "math")
    math_topic = db.get(Topic, math_topic_id)
    original_name = math_topic.name
    math_topic.name = "Drifted demo topic"
    db.commit()
    assert any(item.conflict for item in manager.plan().items)
    math_topic.name = original_name
    db.commit()
    manager.verify()

    dataset_topic_ids = {
        str(stable_uuid(fixture.manifest.namespace, "topic", item.key))
        for item in fixture.topics
    }
    dataset_exam_ids = {
        str(stable_uuid(fixture.manifest.namespace, "exam", item.key))
        for item in fixture.exams
    }
    teacher_topics = client.get("/topics", headers=_headers(teacher))
    admin_topics = client.get("/topics", headers=_headers(admin))
    assert teacher_topics.status_code == 200
    assert admin_topics.status_code == 200
    assert dataset_topic_ids <= {item["id"] for item in teacher_topics.json()["items"]}
    assert dataset_topic_ids <= {item["id"] for item in admin_topics.json()["items"]}

    student_exams = client.get("/student/exams", headers=_headers(student))
    assert student_exams.status_code == 200
    visible_exam_ids = {item["id"] for item in student_exams.json()["items"]}
    published_exam_ids = {
        str(stable_uuid(fixture.manifest.namespace, "exam", item.key))
        for item in fixture.exams if item.is_published
    }
    draft_exam_ids = dataset_exam_ids - published_exam_ids
    assert published_exam_ids <= visible_exam_ids
    assert visible_exam_ids.isdisjoint(draft_exam_ids)

    overview = client.get("/analytics/overview", headers=_headers(teacher))
    score_stats = client.get("/analytics/score-stats", headers=_headers(teacher))
    assert overview.status_code == score_stats.status_code == 200
    assert overview.json()["total_exams"] == 6
    assert overview.json()["total_submissions"] == 15
    distribution = {item["range_label"]: item["count"] for item in score_stats.json()["distribution"]}
    assert sum(count > 0 for count in distribution.values()) >= 4

    math_exam_id = stable_uuid(fixture.manifest.namespace, "exam", "math-published")
    started = client.get(f"/student/exams/{math_exam_id}/start", headers=_headers(api_student))
    assert started.status_code == 200
    assert all(
        "is_correct" not in option
        for question in started.json()["questions"]
        for option in question["options"]
    )

    material_id = stable_uuid(
        fixture.manifest.namespace, "material", "math-limits-text"
    )
    owner_download = client.get(f"/materials/{material_id}/download", headers=_headers(teacher))
    admin_download = client.get(f"/materials/{material_id}/download", headers=_headers(admin))
    denied_download = client.get(
        f"/materials/{material_id}/download", headers=_headers(other_teacher)
    )
    missing_download = client.get(
        f"/materials/{uuid4()}/download", headers=_headers(other_teacher)
    )
    assert owner_download.status_code == 200
    assert admin_download.status_code == 200
    assert denied_download.status_code == missing_download.status_code == 404
    assert denied_download.json()["error_code"] == missing_download.json()["error_code"]

    lesson_topic_id = stable_uuid(fixture.manifest.namespace, "topic", "math-limits")
    decks = client.get(
        f"/flashcards/topics/{lesson_topic_id}/decks", headers=_headers(student)
    )
    assert decks.status_code == 200
    assert len(decks.json()) == 1
    card_id = stable_uuid(fixture.manifest.namespace, "card", "card-math-limits-08")
    review = client.post(
        f"/flashcards/student/cards/{card_id}/review",
        json={"rating": "EASY"},
        headers=_headers(api_student),
    )
    assert review.status_code == 200
    assert review.json()["box_level"] == 2

    with pytest.raises(DemoDataError, match="non-dataset learning records"):
        manager.reset(fixture.manifest.dataset_id)

    db.execute(
        delete(Submission).where(
            Submission.exam_id == math_exam_id,
            Submission.student_id == api_student.id,
        )
    )
    db.execute(
        delete(FlashcardProgress).where(
            FlashcardProgress.student_id == api_student.id,
            FlashcardProgress.flashcard_id == card_id,
        )
    )
    db.commit()

    reset = manager.reset(fixture.manifest.dataset_id)
    assert reset.counts["topics"] == 9
    assert db.get(Topic, unrelated_topic.id) is not None
    assert manager.plan().items[0].create == 9


class FailingStorage(LocalFileStorage):
    def __init__(self, root: Path) -> None:
        super().__init__(root, namespace="demo-standard-v1")
        self.save_count = 0

    def save(self, filename: str, content: bytes) -> str:
        self.save_count += 1
        if self.save_count == 2:
            raise OSError("injected storage failure")
        return super().save(filename, content)


@pytest.mark.integration
def test_demo_dataset_rolls_back_mid_apply(db, demo_accounts, tmp_path: Path) -> None:
    fixture = load_demo_fixture()
    cleanup_manager = DemoDataManager(
        fixture,
        db,
        LocalFileStorage(Path("uploads"), namespace=fixture.manifest.dataset_id),
        database_url="postgresql://test:test@localhost/playstudy_test",
        environment="test",
    )
    if any(item.unchanged or item.conflict for item in cleanup_manager.plan().items):
        cleanup_manager.reset(fixture.manifest.dataset_id)
    storage = FailingStorage(tmp_path / "uploads")
    manager = DemoDataManager(
        fixture,
        db,
        storage,
        database_url="postgresql://test:test@localhost/playstudy_test",
        environment="test",
    )

    with pytest.raises(OSError, match="injected storage failure"):
        manager.apply()

    topic_ids = [
        stable_uuid(fixture.manifest.namespace, "topic", item.key)
        for item in fixture.topics
    ]
    assert db.scalars(select(Topic.id).where(Topic.id.in_(topic_ids))).all() == []
    assert list((tmp_path / "uploads").rglob("*.*")) == []
