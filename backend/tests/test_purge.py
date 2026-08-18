import inspect
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, func, select, update

from app.core.exceptions import AppException
from app.core.file_storage import LocalFileStorage
from app.db.soft_delete import RESTORE_WINDOW
from app.models.audit_event import AuditEvent
from app.models.exam import Exam, Question
from app.models.flashcard import FlashcardDeck
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from app.services import purge_service
from app.services.purge_service import apply_purge, plan_purge
from tests.test_authorization_idor import create_exam, create_teacher, create_topic


def _admin_actor(test_admin):
    return SimpleNamespace(id=test_admin["id"], role="admin")


def _make_storage(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    storage.ensure_root()
    return storage


def _create_material(db, storage, owner_id, *, content=b"purge me"):
    file_path = storage.save(f"{uuid.uuid4()}.txt", content)
    material = StudyMaterial(
        uploader_id=owner_id,
        title=f"Purge material {uuid.uuid4()}.txt",
        file_type="txt",
        file_path=file_path,
        ai_status="completed",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def _soft_delete(db, material, deleted_at, actor_id):
    material.deleted_at = deleted_at
    material.deleted_by_id = actor_id
    db.commit()
    db.refresh(material)


def _get_including_deleted(db, model, resource_id):
    db.expire_all()
    return db.scalar(
        select(model)
        .where(model.id == resource_id)
        .execution_options(include_deleted=True)
    )


def _hard_delete_materials(db, *material_ids):
    """Test-only cleanup, bypassing purge_service entirely.

    `db` is a session-scoped fixture shared by every integration test in
    this run (see `tests/conftest.py`), so a soft-deleted-and-expired
    material left behind by one test is still "eligible" the next time any
    later test calls `apply_purge`/`plan_purge` -- and that later test's own
    `FileStorage` is rooted at a different `tmp_path`, so quarantining a
    leftover row's file would escape its root and blow up. Tests that
    intentionally leave a material eligible-but-unpurged (dry run, blocked,
    injected failure) must scrub it via this helper rather than relying on
    `apply_purge` to remove it.
    """
    if not material_ids:
        return
    db.rollback()
    db.execute(delete(StudyMaterial).where(StudyMaterial.id.in_(material_ids)))
    db.commit()


def test_plan_purge_makes_zero_changes(client, db, tmp_path):
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    material = _create_material(db, storage, owner["id"])
    expired = datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=1)
    _soft_delete(db, material, expired, owner["id"])

    try:
        audit_count_before = db.scalar(select(func.count(AuditEvent.event_id)))
        report = plan_purge(db)
        audit_count_after = db.scalar(select(func.count(AuditEvent.event_id)))

        assert material.id in report.eligible_ids
        assert audit_count_after == audit_count_before

        stored = _get_including_deleted(db, StudyMaterial, material.id)
        assert stored is not None
        assert stored.deleted_at is not None
        assert storage.resolve_for_read(material.file_path).is_file()
    finally:
        # plan_purge is a dry run by design, so this material is still
        # eligible when the test ends -- scrub it so it doesn't trip up a
        # later test's apply_purge call against a different tmp_path root.
        _hard_delete_materials(db, material.id)


def test_apply_purge_exact_boundary(client, db, test_admin, tmp_path):
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)

    not_yet = _create_material(db, storage, owner["id"])
    _soft_delete(
        db,
        not_yet,
        datetime.now(timezone.utc) - RESTORE_WINDOW + timedelta(hours=1),
        owner["id"],
    )

    at_boundary = _create_material(db, storage, owner["id"])
    _soft_delete(
        db,
        at_boundary,
        datetime.now(timezone.utc) - RESTORE_WINDOW,
        owner["id"],
    )

    past_boundary = _create_material(db, storage, owner["id"])
    _soft_delete(
        db,
        past_boundary,
        datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=1),
        owner["id"],
    )

    report = apply_purge(db, admin_actor, storage=storage)

    assert not_yet.id not in report.purged_ids
    assert at_boundary.id in report.purged_ids
    assert past_boundary.id in report.purged_ids

    assert _get_including_deleted(db, StudyMaterial, not_yet.id) is not None
    assert _get_including_deleted(db, StudyMaterial, at_boundary.id) is None
    assert _get_including_deleted(db, StudyMaterial, past_boundary.id) is None


def test_apply_purge_batch_is_idempotent(client, db, test_admin, tmp_path):
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)
    material = _create_material(db, storage, owner["id"])
    _soft_delete(
        db,
        material,
        datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=1),
        owner["id"],
    )

    first = apply_purge(db, admin_actor, storage=storage)
    assert material.id in first.purged_ids
    assert _get_including_deleted(db, StudyMaterial, material.id) is None

    second = apply_purge(db, admin_actor, storage=storage)
    assert material.id not in second.purged_ids
    assert material.id not in second.eligible_ids


def test_apply_purge_mid_failure_leaves_recoverable_quarantine(
    client, db, test_admin, tmp_path, monkeypatch
):
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)
    material = _create_material(db, storage, owner["id"], content=b"quarantine me")
    original_path = material.file_path
    expired = datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=1)
    _soft_delete(db, material, expired, owner["id"])

    original_record = purge_service.AuditService.record

    def failing_record(db_arg, event):
        result = original_record(db_arg, event)
        if event.action == "purge.completed":
            raise RuntimeError("simulated mid-purge failure")
        return result

    monkeypatch.setattr(
        purge_service.AuditService, "record", staticmethod(failing_record)
    )

    try:
        with pytest.raises(RuntimeError, match="simulated mid-purge failure"):
            apply_purge(db, admin_actor, storage=storage)

        monkeypatch.undo()

        # The material row is untouched: still present, still soft-deleted
        # at exactly the same timestamp it had before the failed attempt.
        stored = _get_including_deleted(db, StudyMaterial, material.id)
        assert stored is not None
        assert stored.deleted_at is not None
        assert abs((stored.deleted_at - expired).total_seconds()) < 1

        # The file was pulled out of active storage during the attempt but
        # is fully recoverable -- apply_purge moves it back to its original
        # path on failure rather than leaving it stranded in quarantine or
        # deleting it.
        assert storage.resolve_for_read(original_path).is_file()
    finally:
        # Still eligible (the purge attempt was rolled back) -- scrub it so
        # it doesn't trip up a later test's apply_purge call against a
        # different tmp_path root.
        _hard_delete_materials(db, material.id)


def test_apply_purge_denies_non_admin(client, db, test_teacher, test_student, tmp_path):
    storage = _make_storage(tmp_path)
    teacher_actor = SimpleNamespace(id=test_teacher["id"], role="teacher")
    student_actor = SimpleNamespace(id=test_student["id"], role="student")

    with pytest.raises(AppException) as teacher_exc:
        apply_purge(db, teacher_actor, storage=storage)
    assert teacher_exc.value.status_code == 403

    with pytest.raises(AppException) as student_exc:
        apply_purge(db, student_actor, storage=storage)
    assert student_exc.value.status_code == 403


def test_material_with_retained_links_is_blocked_not_purged(
    client, db, test_admin, tmp_path
):
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)

    material_topic = Topic(
        owner_id=owner["id"], name=f"Purge guard topic {uuid.uuid4()}"
    )
    material = StudyMaterial(
        uploader_id=owner["id"],
        title="retained-purge.txt",
        file_type="txt",
        file_path=storage.save(f"{uuid.uuid4()}.txt", b"still linked"),
        ai_status="completed",
    )
    db.add_all([material_topic, material])
    db.flush()
    deck = FlashcardDeck(
        topic_id=material_topic.id,
        material_id=material.id,
        title="Retained deck",
    )
    db.add(deck)
    db.flush()

    expired = datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=2)
    material.deleted_at = expired
    material.deleted_by_id = owner["id"]
    db.commit()

    try:
        plan = plan_purge(db)
        assert material.id in plan.blocked_ids
        assert material.id not in plan.eligible_ids

        report = apply_purge(db, admin_actor, storage=storage)
        assert material.id in report.blocked_ids
        assert material.id not in report.purged_ids

        stored = _get_including_deleted(db, StudyMaterial, material.id)
        assert stored is not None
        assert stored.deleted_at is not None
    finally:
        # The retained link (the deck) keeps this material permanently
        # blocked, not just for this test -- scrub both so a later test's
        # apply_purge call doesn't keep re-discovering it.
        db.rollback()
        db.execute(delete(FlashcardDeck).where(FlashcardDeck.id == deck.id))
        db.execute(
            delete(StudyMaterial).where(StudyMaterial.id == material.id)
        )
        db.execute(delete(Topic).where(Topic.id == material_topic.id))
        db.commit()


def test_apply_purge_emits_requested_and_completed_audit_events(
    client, db, test_admin, tmp_path
):
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)
    material = _create_material(db, storage, owner["id"])
    original_path = material.file_path
    expired = datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=3)
    _soft_delete(db, material, expired, owner["id"])

    request_id = str(uuid.uuid4())
    report = apply_purge(db, admin_actor, storage=storage, request_id=request_id)
    assert material.id in report.purged_ids

    events = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.request_id == request_id,
            AuditEvent.entity_id == str(material.id),
        )
        .order_by(AuditEvent.occurred_at)
    ).all()
    actions = [event.action for event in events]
    assert actions == ["purge.requested", "purge.completed"]
    for event in events:
        assert event.outcome == "success"
        assert event.actor_role == "admin"
        assert event.actor_id == admin_actor.id
        assert event.entity_type == "study_material"
        assert event.owner_id == owner["id"]
    assert events[1].event_metadata["quarantined"] is True

    with pytest.raises(FileNotFoundError):
        storage.resolve_for_read(original_path)


def test_purge_never_touches_other_governed_roots(
    client, db, test_admin, tmp_path
):
    owner = create_teacher(client, db)
    other_owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)

    topic = create_topic(client, owner, f"Purge guard topic {uuid.uuid4()}")
    exam = create_exam(client, owner, f"Purge guard exam {uuid.uuid4()}")

    expired = datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=5)
    db.execute(
        update(Topic)
        .where(Topic.id == uuid.UUID(topic["id"]))
        .values(deleted_at=expired)
    )
    db.execute(
        update(Exam)
        .where(Exam.id == uuid.UUID(exam["id"]))
        .values(deleted_at=expired)
    )
    db.execute(
        update(User).where(User.id == other_owner["id"]).values(deleted_at=expired)
    )
    db.commit()

    topic_count_before = db.scalar(
        select(func.count(Topic.id)).execution_options(include_deleted=True)
    )
    exam_count_before = db.scalar(
        select(func.count(Exam.id)).execution_options(include_deleted=True)
    )
    question_count_before = db.scalar(
        select(func.count(Question.id)).execution_options(include_deleted=True)
    )
    user_count_before = db.scalar(
        select(func.count(User.id)).execution_options(include_deleted=True)
    )
    audit_count_before = db.scalar(select(func.count(AuditEvent.event_id)))

    material = _create_material(db, storage, owner["id"])
    _soft_delete(db, material, expired, owner["id"])

    report = apply_purge(db, admin_actor, storage=storage)
    assert material.id in report.purged_ids

    topic_count_after = db.scalar(
        select(func.count(Topic.id)).execution_options(include_deleted=True)
    )
    exam_count_after = db.scalar(
        select(func.count(Exam.id)).execution_options(include_deleted=True)
    )
    question_count_after = db.scalar(
        select(func.count(Question.id)).execution_options(include_deleted=True)
    )
    user_count_after = db.scalar(
        select(func.count(User.id)).execution_options(include_deleted=True)
    )
    audit_count_after = db.scalar(select(func.count(AuditEvent.event_id)))

    assert topic_count_after == topic_count_before
    assert exam_count_after == exam_count_before
    assert question_count_after == question_count_before
    assert user_count_after == user_count_before
    # Exactly two new audit rows for the one purged material -- purge never
    # deletes or mutates existing audit_events (the table is append-only at
    # the database level besides).
    assert audit_count_after == audit_count_before + 2

    assert _get_including_deleted(db, Topic, uuid.UUID(topic["id"])) is not None
    assert _get_including_deleted(db, Exam, uuid.UUID(exam["id"])) is not None
    assert _get_including_deleted(db, User, other_owner["id"]) is not None


def test_purge_service_source_never_deletes_protected_models():
    """Static regression guard: the allowlist can't be silently widened.

    `apply_purge` must never issue a `delete(...)` against any governed root
    other than `StudyMaterial`. This inspects the actual module source
    rather than trusting a comment, so it fails loudly if a future edit adds
    a stray `delete(Exam)`/`delete(User)`/etc. alongside it.
    """
    source = inspect.getsource(purge_service)
    forbidden_deletes = (
        "delete(Exam",
        "delete(User",
        "delete(Submission",
        "delete(AuditEvent",
        "delete(Question",
        "delete(Topic",
    )
    for token in forbidden_deletes:
        assert token not in source, f"purge_service must never {token}...)"
    assert "delete(StudyMaterial" in source
