import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Event

import pytest
from sqlalchemy import func, select
from app.api.deps import get_current_user
from app.core.exceptions import AppException
from app.db.session import SessionLocal
from app.models.ai_generation import AIGenerationJob
from app.models.audit_event import AuditEvent
from app.models.exam import Question
from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from app.services.ai_generation_service import AIGenerationService
from app.services.ai_service import mock_generate_topic_kit
from app.services.authorization_service import AuthorizationService
from app.services.flashcard_service import FlashcardService
from app.services.material_service import MaterialService
from app.services.user_service import UserService

AI_DRAFT = {
    "questions": [
        {
            "type": "MULTIPLE_CHOICE",
            "content": "Which planet is closest to the sun?",
            "points": 1,
            "options": [
                {"content": "Mercury", "is_correct": True},
                {"content": "Neptune", "is_correct": False},
            ],
        },
        {
            "type": "MULTIPLE_CHOICE",
            "content": "How many continents are there?",
            "points": 1,
            "options": [
                {"content": "Seven", "is_correct": True},
                {"content": "Three", "is_correct": False},
            ],
        },
    ]
}


def _awaiting_review_job(db, owner_id):
    """An AI generation job parked at `awaiting_review`, fully committed."""
    material = StudyMaterial(
        uploader_id=owner_id,
        title=f"concurrent-review-{uuid.uuid4()}.txt",
        file_type="txt",
        file_path=f"uploads/materials/concurrent-review-{uuid.uuid4()}.txt",
        ai_status="completed",
    )
    db.add(material)
    db.commit()
    actor = db.get(User, owner_id)
    assert actor is not None

    job = AIGenerationService.create_job(
        db,
        owner_id=owner_id,
        material_id=material.id,
        use_case="question_generation",
    )
    AIGenerationService.commit_transition(db, job, "processing", actor=actor)
    AIGenerationService.commit_transition(
        db, job, "generated", actor=actor, draft_payload=AI_DRAFT
    )
    AIGenerationService.commit_transition(db, job, "awaiting_review", actor=actor)
    return job.id, material.id


def _pause_transition_on(monkeypatch, target_status, ready, release):
    """Hold the first transition to `target_status` open inside its lock.

    `_review_decision`/`publish_generation_job` take the row lock in
    `get_job_for_review(lock=True)` and only then call `commit_transition`,
    so pausing at its entry parks the first actor mid-transaction with the
    lock held -- which is exactly the window a second reviewer would race
    into.
    """
    original = AIGenerationService.commit_transition
    state = {"paused": False}

    def paused_commit_transition(session, job, status, **kwargs):
        if status == target_status and not state["paused"]:
            state["paused"] = True
            ready.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Timed out waiting to release the first actor")
        return original(session, job, status, **kwargs)

    monkeypatch.setattr(
        AIGenerationService, "commit_transition", paused_commit_transition
    )
    return original


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
    # StudyMaterial is a governed soft-delete root (DATA-003): the cascade
    # marks it deleted rather than removing the row, so a default read must
    # exclude it while the row itself remains present and flagged deleted.
    assert db.scalar(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
    ) is None
    soft_deleted_material = db.scalar(
        select(StudyMaterial)
        .where(StudyMaterial.id == material_id)
        .execution_options(include_deleted=True)
    )
    assert soft_deleted_material is not None
    assert soft_deleted_material.deleted_at is not None
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
    # AI-002 routed the topic-kit worker through the review queue, so its
    # commit boundary is now `commit_with_audit` rather than
    # `commit_with_admin_override`. The invariant under test is unchanged:
    # the worker's `with_for_update` lock on the acting user must serialize
    # a concurrent demotion behind it. Only the pause point moved. Pause on
    # the first call so the lock is held while the demotion is attempted.
    original_commit = AuthorizationService.commit_with_audit
    paused_once = Event()

    def paused_commit(session, **kwargs):
        if not paused_once.is_set():
            paused_once.set()
            worker_ready.set()
            if not release_worker.wait(timeout=5):
                raise RuntimeError(
                    "Timed out waiting to release background worker"
                )
        return original_commit(session, **kwargs)

    monkeypatch.setattr(
        AuthorizationService,
        "commit_with_audit",
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


def test_concurrent_approvals_of_one_generation_job_leave_a_single_decision(
    db,
    test_teacher,
    test_admin,
    monkeypatch,
):
    """Two reviewers approving at once: one decision, one reviewer, one event.

    The second approval must not silently overwrite the first reviewer's
    identity -- `reviewer_id` is the record of who signed off, so a
    last-writer-wins race would misattribute the decision.
    """
    job_id, material_id = _awaiting_review_job(db, test_teacher["id"])

    first_locked = Event()
    release_first = Event()
    _pause_transition_on(monkeypatch, "approved", first_locked, release_first)

    def approve_as(user_id) -> str:
        with SessionLocal() as session:
            actor = session.get(User, user_id)
            assert actor is not None
            try:
                MaterialService.approve_generation_job(session, job_id, actor)
            except AppException as exc:
                session.rollback()
                return exc.error_code
            return "approved"

    with ThreadPoolExecutor(max_workers=2) as executor:
        winner = executor.submit(approve_as, test_teacher["id"])
        assert first_locked.wait(timeout=5)
        loser = executor.submit(approve_as, test_admin["id"])
        try:
            # Blocked on the row lock the first approval holds.
            assert_future_is_blocked(loser)
        finally:
            release_first.set()
        assert winner.result(timeout=5) == "approved"
        # Once the lock lifts, the second reviewer re-reads an `approved`
        # row, and approved -> approved is not in the allowlist.
        assert loser.result(timeout=5) == "AI_JOB_INVALID_TRANSITION"

    db.expire_all()
    job = db.get(AIGenerationJob, job_id)
    assert job.status == "approved"
    assert job.reviewer_id == test_teacher["id"]
    # requested -> processing -> generated -> awaiting_review -> approved.
    assert job.version == 5

    approvals = db.scalar(
        select(func.count(AuditEvent.event_id)).where(
            AuditEvent.entity_type == "ai_generation_job",
            AuditEvent.entity_id == str(job_id),
            AuditEvent.action == "ai.generation.approved",
        )
    )
    assert approvals == 1
    # The losing approval published nothing on its way to being refused.
    assert db.scalar(
        select(func.count(Question.id)).where(Question.material_id == material_id)
    ) == 0


def test_concurrent_publishes_of_one_generation_job_write_one_set_of_rows(
    db,
    test_teacher,
    test_admin,
    monkeypatch,
):
    """The double-publish race: two publishers, one set of questions."""
    job_id, material_id = _awaiting_review_job(db, test_teacher["id"])
    actor = db.get(User, test_teacher["id"])
    MaterialService.approve_generation_job(db, job_id, actor)

    first_locked = Event()
    release_first = Event()
    _pause_transition_on(monkeypatch, "published", first_locked, release_first)

    def publish_as(user_id) -> str:
        with SessionLocal() as session:
            publisher = session.get(User, user_id)
            assert publisher is not None
            try:
                MaterialService.publish_generation_job(
                    session, job_id, publisher
                )
            except AppException as exc:
                session.rollback()
                return exc.error_code
            return "published"

    with ThreadPoolExecutor(max_workers=2) as executor:
        winner = executor.submit(publish_as, test_teacher["id"])
        assert first_locked.wait(timeout=5)
        loser = executor.submit(publish_as, test_admin["id"])
        try:
            assert_future_is_blocked(loser)
        finally:
            release_first.set()
        assert winner.result(timeout=5) == "published"
        assert loser.result(timeout=5) == "AI_JOB_INVALID_TRANSITION"

    db.expire_all()
    # The decisive assertion: the draft holds two questions, and exactly two
    # questions exist. A second publish would have made four.
    assert db.scalar(
        select(func.count(Question.id)).where(Question.material_id == material_id)
    ) == 2
    job = db.get(AIGenerationJob, job_id)
    assert job.status == "published"
    assert job.published_at is not None
    published_events = db.scalar(
        select(func.count(AuditEvent.event_id)).where(
            AuditEvent.entity_type == "ai_generation_job",
            AuditEvent.entity_id == str(job_id),
            AuditEvent.action == "ai.generation.published",
        )
    )
    assert published_events == 1
