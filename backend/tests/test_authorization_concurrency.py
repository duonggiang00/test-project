import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Event

import pytest
from sqlalchemy import select
from app.api.deps import get_current_user
from app.core.exceptions import AppException
from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from app.services.ai_service import mock_generate_topic_kit
from app.services.authorization_service import AuthorizationService
from app.services.flashcard_service import FlashcardService
from app.services.material_service import MaterialService
from app.services.user_service import UserService


class NoopStorage:
    def delete(self, _stored_path: str) -> None:
        return None


def assert_future_is_blocked(future) -> None:
    with pytest.raises(FutureTimeout):
        future.result(timeout=0.25)


def test_authenticated_content_write_serializes_against_role_demotion(
    db,
    test_teacher,
    test_admin,
):
    writer_ready = Event()
    release_writer = Event()

    def write_owned_content() -> None:
        with SessionLocal() as session:
            actor = get_current_user(session, test_teacher["token"])
            session.add(
                Topic(
                    owner_id=actor.id,
                    name=f"Concurrent owner topic {uuid.uuid4()}",
                )
            )
            writer_ready.set()
            if not release_writer.wait(timeout=5):
                raise RuntimeError("Timed out waiting to release content write")
            session.commit()

    def demote_teacher() -> str:
        with SessionLocal() as session:
            operator = session.get(User, test_admin["id"])
            assert operator is not None
            try:
                UserService.update_user_role(
                    session,
                    test_teacher["id"],
                    "student",
                    operator,
                )
            except AppException as exc:
                session.rollback()
                return exc.error_code
            return "unexpected-success"

    with ThreadPoolExecutor(max_workers=2) as executor:
        writer = executor.submit(write_owned_content)
        assert writer_ready.wait(timeout=5)
        demotion = executor.submit(demote_teacher)
        try:
            assert_future_is_blocked(demotion)
        finally:
            release_writer.set()
        writer.result(timeout=5)
        assert (
            demotion.result(timeout=5)
            == "USER_ROLE_CHANGE_BLOCKED_BY_OWNED_DATA"
        )

    db.expire_all()
    assert db.get(User, test_teacher["id"]).role == "teacher"


def test_material_cascade_serializes_concurrent_flashcard_review(
    db,
    test_teacher,
    test_student,
):
    topic = Topic(
        owner_id=test_teacher["id"],
        name=f"Concurrent material topic {uuid.uuid4()}",
    )
    material = StudyMaterial(
        uploader_id=test_teacher["id"],
        title="concurrent.txt",
        file_type="txt",
        file_path="uploads/materials/concurrent.txt",
        ai_status="completed",
    )
    db.add_all([topic, material])
    db.flush()
    deck = FlashcardDeck(
        topic_id=topic.id,
        material_id=material.id,
        title="Concurrent deck",
    )
    db.add(deck)
    db.flush()
    card = Flashcard(
        deck_id=deck.id,
        front_content="Front",
        back_content="Back",
    )
    db.add(card)
    db.commit()
    material_id = material.id
    card_id = card.id

    unsafe_check_complete = Event()
    release_delete = Event()

    def cascade_material() -> str:
        with SessionLocal() as session:
            actor = session.get(User, test_teacher["id"])
            assert actor is not None
            original_scalar = session.scalar

            def intercept_scalar(statement, *args, **kwargs):
                result = original_scalar(statement, *args, **kwargs)
                rendered = str(statement).casefold()
                if (
                    "flashcard_progress" in rendered
                    and "exists" in rendered
                    and not unsafe_check_complete.is_set()
                ):
                    unsafe_check_complete.set()
                    if not release_delete.wait(timeout=5):
                        raise RuntimeError(
                            "Timed out waiting to release material cascade"
                        )
                return result

            session.scalar = intercept_scalar
            MaterialService.delete_material(
                session,
                material_id,
                actor,
                cascade=True,
                storage=NoopStorage(),
            )
            return "deleted"

    def review_card() -> str:
        with SessionLocal() as session:
            student = session.get(User, uuid.UUID(test_student["id"]))
            assert student is not None
            try:
                FlashcardService.review_card(
                    session,
                    card_id,
                    student,
                    "GOOD",
                )
            except AppException as exc:
                session.rollback()
                return exc.error_code
            return "unexpected-success"

    with ThreadPoolExecutor(max_workers=2) as executor:
        deletion = executor.submit(cascade_material)
        assert unsafe_check_complete.wait(timeout=5)
        review = executor.submit(review_card)
        try:
            assert_future_is_blocked(review)
        finally:
            release_delete.set()
        assert deletion.result(timeout=5) == "deleted"
        assert review.result(timeout=5) == "FLASHCARD_NOT_FOUND"

    db.expire_all()
    assert db.get(StudyMaterial, material_id) is None
    assert db.get(Flashcard, card_id) is None
    assert db.scalar(
        select(FlashcardProgress.id).where(
            FlashcardProgress.flashcard_id == card_id
        )
    ) is None


def test_background_admin_override_serializes_against_demotion(
    db,
    test_teacher,
    test_admin,
    monkeypatch,
):
    operator = User(
        email=f"concurrency-admin-{uuid.uuid4()}@example.com",
        password_hash="not-used",
        full_name="Concurrency Admin",
        role="admin",
    )
    topic = Topic(
        owner_id=test_teacher["id"],
        name=f"Concurrent background topic {uuid.uuid4()}",
    )
    material = StudyMaterial(
        uploader_id=test_teacher["id"],
        title="background-concurrency.txt",
        file_type="txt",
        file_path="uploads/materials/background-concurrency.txt",
        ai_status="completed",
    )
    db.add_all([operator, topic, material])
    db.commit()
    request_id = str(uuid.uuid4())

    worker_ready = Event()
    release_worker = Event()
    original_commit = AuthorizationService.commit_with_admin_override

    def paused_commit(session, **kwargs):
        worker_ready.set()
        if not release_worker.wait(timeout=5):
            raise RuntimeError("Timed out waiting to release background worker")
        return original_commit(session, **kwargs)

    monkeypatch.setattr("app.services.ai_service.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        AuthorizationService,
        "commit_with_admin_override",
        paused_commit,
    )

    def generate_topic_kit() -> None:
        mock_generate_topic_kit(
            str(material.id),
            str(topic.id),
            str(test_teacher["id"]),
            str(test_admin["id"]),
            request_id,
        )

    def demote_background_actor() -> str:
        with SessionLocal() as session:
            admin_operator = session.get(User, operator.id)
            assert admin_operator is not None
            updated = UserService.update_user_role(
                session,
                test_admin["id"],
                "teacher",
                admin_operator,
            )
            return updated.role

    with ThreadPoolExecutor(max_workers=2) as executor:
        worker = executor.submit(generate_topic_kit)
        assert worker_ready.wait(timeout=5)
        demotion = executor.submit(demote_background_actor)
        try:
            assert_future_is_blocked(demotion)
        finally:
            release_worker.set()
        worker.result(timeout=5)
        assert demotion.result(timeout=5) == "teacher"

    db.expire_all()
    assert db.get(User, test_admin["id"]).role == "teacher"
    event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.request_id == request_id,
            AuditEvent.action == "admin.override",
        )
    )
    assert event is not None
    assert event.actor_role == "admin"
    assert event.owner_id == test_teacher["id"]
