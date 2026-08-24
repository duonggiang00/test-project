"""PostgreSQL concurrency contracts for the Student exam lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.submission import Submission, SubmissionAnswer
from app.services.grading_service import GradingService


def test_concurrent_start_and_submit_are_idempotent_and_serialized(
    client,
    db,
    sample_exam,
    test_student,
    monkeypatch,
) -> None:
    """Two real Sessions must converge on one retained submission and grade."""

    del client  # Activates the module TestClient fixture and its dependencies.
    start_commit_barrier = Barrier(2)

    class CoordinatedSession(Session):
        def commit(self) -> None:
            if any(isinstance(item, Submission) for item in self.new):
                start_commit_barrier.wait(timeout=10)
            super().commit()

    request_session = sessionmaker(
        bind=db.get_bind(),
        class_=CoordinatedSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db():
        request_db = request_session()
        try:
            yield request_db
        finally:
            request_db.close()

    original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    request_engine = db.get_bind()
    exam_id = sample_exam["exam"]["id"]
    headers = test_student["headers"]

    try:
        with TestClient(app) as first_client, TestClient(app) as second_client:
            with ThreadPoolExecutor(max_workers=2) as executor:
                start_responses = list(
                    executor.map(
                        lambda local_client: local_client.get(
                            f"/student/exams/{exam_id}/start",
                            headers=headers,
                        ),
                        (first_client, second_client),
                    )
                )

            assert [response.status_code for response in start_responses] == [200, 200]
            db.expire_all()
            submissions = list(
                db.scalars(
                    select(Submission).where(
                        Submission.exam_id == UUID(exam_id),
                        Submission.student_id == UUID(test_student["id"]),
                    )
                ).all()
            )
            assert len(submissions) == 1

            question = sample_exam["questions"][0]
            correct_option_id = next(
                option["id"] for option in question["options"] if option["is_correct"]
            )
            payload = {
                "answers": [
                    {
                        "question_id": question["id"],
                        "answer_data": {"selected_option_id": correct_option_id},
                    }
                ]
            }

            first_grading_started = Event()
            second_lock_attempted = Event()
            lock_attempt_count = 0
            lock_attempt_guard = Lock()
            original_grade_question = GradingService.grade_question

            def observe_submission_lock(
                _connection,
                _cursor,
                statement,
                _parameters,
                _context,
                _executemany,
            ) -> None:
                nonlocal lock_attempt_count
                normalized = " ".join(statement.lower().split())
                if "from submissions" not in normalized or "for update" not in normalized:
                    return
                with lock_attempt_guard:
                    lock_attempt_count += 1
                    if lock_attempt_count == 2:
                        second_lock_attempted.set()

            def block_first_grader(question, answer_data):
                if not first_grading_started.is_set():
                    first_grading_started.set()
                    assert second_lock_attempted.wait(timeout=10), (
                        "The second submit never attempted to lock the Submission row"
                    )
                return original_grade_question(question, answer_data)

            event.listen(
                request_engine,
                "before_cursor_execute",
                observe_submission_lock,
            )
            monkeypatch.setattr(
                GradingService,
                "grade_question",
                staticmethod(block_first_grader),
            )

            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    submit_responses = list(
                        executor.map(
                            lambda local_client: local_client.post(
                                f"/student/exams/{exam_id}/submit",
                                json=payload,
                                headers=headers,
                            ),
                            (first_client, second_client),
                        )
                    )
            finally:
                event.remove(
                    request_engine,
                    "before_cursor_execute",
                    observe_submission_lock,
                )

        statuses = sorted(response.status_code for response in submit_responses)
        assert statuses == [200, 400]
        rejected = next(
            response for response in submit_responses if response.status_code == 400
        )
        assert rejected.json()["error_code"] == "ALREADY_SUBMITTED"

        db.expire_all()
        submission = db.scalar(
            select(Submission).where(
                Submission.exam_id == UUID(exam_id),
                Submission.student_id == UUID(test_student["id"]),
            )
        )
        assert submission is not None
        assert submission.status == "submitted"
        assert db.scalar(
            select(func.count(SubmissionAnswer.id)).where(
                SubmissionAnswer.submission_id == submission.id
            )
        ) == 1
        assert db.scalar(
            select(func.count(AuditEvent.event_id)).where(
                AuditEvent.action == "submission.graded",
                AuditEvent.entity_id == str(submission.id),
            )
        ) == 1
    finally:
        if original_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = original_override
