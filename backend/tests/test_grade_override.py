"""Teacher corrects a stored grade (GRADE-001).

`points_awarded` used to be written once at submit time and never again, so a
wrongly-graded answer -- most realistically a `FILL_IN_BLANK` scored by exact
string match -- was permanent on a record the MVP retention policy keeps
forever. `CANONICAL_PROJECT_SPEC.md` §10.3 flow 4 requires the teacher to be
able to grade the result, and §6 requires the change to be audited.

These tests pin the parts that are easy to get quietly wrong: that the total
is recomputed rather than trusted, that `status` is left alone so analytics
keeps seeing the submission, that the reason never reaches `audit_events`,
and that the ownership boundary holds.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.audit_event import AuditEvent
from app.models.submission import Submission, SubmissionAnswer
from tests.test_authorization_idor import create_exam, create_teacher, create_topic


def _exam_with_two_questions(client, teacher):
    topic = create_topic(client, teacher, f"Grade override {uuid.uuid4()}")
    exam = create_exam(
        client,
        teacher,
        f"Grade override exam {uuid.uuid4()}",
        topic_id=topic["id"],
        published=True,
    )
    questions = []
    for index in range(2):
        response = client.post(
            f"/exams/{exam['id']}/questions",
            json={
                "content": f"Cau hoi {index}",
                "question_type": "SINGLE_CHOICE",
                "points": 10,
                "options": [
                    {"content": "Dung", "is_correct": True},
                    {"content": "Sai", "is_correct": False},
                ],
            },
            headers=teacher["headers"],
        )
        assert response.status_code in (200, 201), response.text
        questions.append(response.json())
    return exam, questions


def _submit_all_wrong(client, student, exam, questions):
    assert (
        client.get(
            f"/student/exams/{exam['id']}/start", headers=student["headers"]
        ).status_code
        == 200
    )
    answers = []
    for question in questions:
        wrong = next(
            opt["id"] for opt in question["options"] if not opt["is_correct"]
        )
        answers.append(
            {
                "question_id": question["id"],
                "answer_data": {"selected_option_id": wrong},
            }
        )
    response = client.post(
        f"/student/exams/{exam['id']}/submit",
        json={"answers": answers},
        headers=student["headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def _override(
    client, actor, submission_id, question_id, points, reason, *, extra_headers=None
):
    headers = {**actor["headers"], **(extra_headers or {})}
    return client.put(
        f"/history/submissions/{submission_id}/answers/{question_id}/grade",
        json={"points_awarded": points, "reason": reason},
        headers=headers,
    )


def _submission_id(client, teacher, exam_id):
    listed = client.get(
        f"/history/submissions?exam_id={exam_id}", headers=teacher["headers"]
    )
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items, "expected the submission to be visible to its exam owner"
    return items[0]["id"]


@pytest.fixture
def graded_submission(client, db, test_student):
    teacher = create_teacher(client, db)
    exam, questions = _exam_with_two_questions(client, teacher)
    _submit_all_wrong(client, test_student, exam, questions)
    submission_id = _submission_id(client, teacher, exam["id"])
    return {
        "teacher": teacher,
        "exam": exam,
        "questions": questions,
        "submission_id": submission_id,
    }


@pytest.mark.integration
def test_owner_correcting_one_answer_recomputes_the_total(client, graded_submission):
    ctx = graded_submission
    response = _override(
        client,
        ctx["teacher"],
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        10,
        "Dap an cua hoc sinh dung theo cach dien dat khac",
    )
    assert response.status_code == 200, response.text
    body = response.json()

    # The total is the sum of its parts, never a client assertion.
    assert body["total_score"] == 10.0
    corrected = next(
        a for a in body["answers"] if a["question_id"] == ctx["questions"][0]["id"]
    )
    assert corrected["points_awarded"] == 10.0
    assert corrected["is_correct"] is True
    assert corrected["override_reason"].startswith("Dap an")
    assert corrected["overridden_at"] is not None
    assert corrected["max_points"] == 10.0

    # The untouched answer is genuinely untouched.
    other = next(
        a for a in body["answers"] if a["question_id"] == ctx["questions"][1]["id"]
    )
    assert other["points_awarded"] == 0.0
    assert other["override_reason"] is None


@pytest.mark.integration
def test_the_submission_status_is_left_alone_so_analytics_still_counts_it(
    client, db, graded_submission
):
    """Analytics aggregates only `status == "submitted"` in three live queries."""
    ctx = graded_submission
    assert (
        _override(
            client,
            ctx["teacher"],
            ctx["submission_id"],
            ctx["questions"][0]["id"],
            10,
            "Cham lai",
        ).status_code
        == 200
    )

    db.expire_all()
    submission = db.get(Submission, uuid.UUID(ctx["submission_id"]))
    assert submission.status == "submitted"

    stats = client.get("/analytics/score-stats", headers=ctx["teacher"]["headers"])
    assert stats.status_code == 200
    assert stats.json()["highest_score"] == 10.0


@pytest.mark.integration
@pytest.mark.parametrize(
    "points,expected_status",
    [(-1, 422), (10.5, 422), (0, 200), (10, 200)],
    ids=["negative", "above-max", "exact-zero", "exact-max"],
)
def test_points_are_bounded_by_the_questions_own_maximum(
    client, graded_submission, points, expected_status
):
    ctx = graded_submission
    response = _override(
        client,
        ctx["teacher"],
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        points,
        "Kiem tra bien",
    )
    assert response.status_code == expected_status, response.text


@pytest.mark.integration
def test_a_multiline_reason_with_an_email_is_stored_and_never_audited(
    client, db, graded_submission
):
    """The reason is business data, not audit metadata.

    `safe_payload` rejects control characters, emails, and path-shaped
    tokens, so routing a typed reason through `audit_events` would turn an
    ordinary correction into a 500. This asserts both halves: the write
    succeeds, and the text appears in no audit row.
    """
    ctx = graded_submission
    canary = "GRADE-CANARY-9f3a"
    reason = f"Da trao doi voi phu huynh\n{canary} lien he giaovien@example.com"

    response = _override(
        client,
        ctx["teacher"],
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        10,
        reason,
    )
    assert response.status_code == 200, response.text

    db.expire_all()
    stored = db.scalar(
        select(SubmissionAnswer).where(
            SubmissionAnswer.submission_id == uuid.UUID(ctx["submission_id"]),
            SubmissionAnswer.question_id == uuid.UUID(ctx["questions"][0]["id"]),
        )
    )
    assert canary in stored.override_reason
    assert stored.overridden_by_id == ctx["teacher"]["id"]

    for event in db.scalars(select(AuditEvent)).all():
        assert canary not in f"{event.changes!r} {event.event_metadata!r}"


@pytest.mark.integration
def test_exactly_one_audit_event_is_written_with_safe_scalars_only(
    client, db, graded_submission
):
    ctx = graded_submission
    request_id = str(uuid.uuid4())
    response = _override(
        client,
        ctx["teacher"],
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        10,
        "Cham lai cau nay",
        extra_headers={"X-Request-ID": request_id},
    )
    assert response.status_code == 200, response.text

    db.expire_all()
    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.request_id == request_id,
            AuditEvent.action == "submission.grade_override",
        )
    ).all()
    assert len(events) == 1
    event = events[0]
    assert event.entity_type == "submission"
    assert event.entity_id == ctx["submission_id"]
    assert event.actor_role == "teacher"
    # owner_id is the exam creator, not the student -- the grading permission
    # is evaluated against exam ownership.
    assert event.owner_id == ctx["teacher"]["id"]
    assert event.changes["points_awarded"] == {"before": 0.0, "after": 10.0}
    assert event.changes["total_score"] == {"before": 0.0, "after": 10.0}
    assert set(event.event_metadata) == {"question_id", "max_score"}


@pytest.mark.integration
def test_a_refused_override_writes_nothing(client, db, graded_submission):
    ctx = graded_submission
    request_id = str(uuid.uuid4())
    response = _override(
        client,
        ctx["teacher"],
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        999,
        "Vuot bien",
        extra_headers={"X-Request-ID": request_id},
    )
    assert response.status_code == 422

    db.expire_all()
    assert (
        db.scalars(
            select(AuditEvent).where(AuditEvent.request_id == request_id)
        ).all()
        == []
    )
    submission = db.get(Submission, uuid.UUID(ctx["submission_id"]))
    assert submission.total_score == 0.0


@pytest.mark.integration
def test_admin_may_correct_and_a_non_owning_teacher_may_not(
    client, db, graded_submission, test_admin
):
    ctx = graded_submission
    stranger = create_teacher(client, db)

    denied = _override(
        client,
        stranger,
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        10,
        "Khong phai de cua toi",
    )
    missing = _override(
        client,
        stranger,
        str(uuid.uuid4()),
        ctx["questions"][0]["id"],
        10,
        "Khong ton tai",
    )
    # Cross-owner and missing are indistinguishable.
    assert denied.status_code == missing.status_code == 404
    assert denied.json()["error_code"] == missing.json()["error_code"]

    allowed = _override(
        client,
        test_admin,
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        10,
        "Admin dieu chinh",
    )
    assert allowed.status_code == 200, allowed.text


@pytest.mark.integration
def test_a_student_cannot_correct_their_own_grade(
    client, graded_submission, test_student
):
    ctx = graded_submission
    response = _override(
        client,
        test_student,
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        10,
        "Cho toi diem cao",
    )
    assert response.status_code == 403


@pytest.mark.integration
def test_an_anonymous_caller_is_rejected(client, graded_submission):
    ctx = graded_submission
    response = client.put(
        f"/history/submissions/{ctx['submission_id']}"
        f"/answers/{ctx['questions'][0]['id']}/grade",
        json={"points_awarded": 10, "reason": "An danh"},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_a_blank_reason_is_refused(client, graded_submission):
    ctx = graded_submission
    response = _override(
        client,
        ctx["teacher"],
        ctx["submission_id"],
        ctx["questions"][0]["id"],
        10,
        "   ",
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_correcting_an_answer_that_is_not_in_this_submission_is_not_found(
    client, graded_submission
):
    ctx = graded_submission
    response = _override(
        client,
        ctx["teacher"],
        ctx["submission_id"],
        str(uuid.uuid4()),
        10,
        "Cau khong thuoc bai nay",
    )
    assert response.status_code == 404


@pytest.mark.integration
def test_two_reviewers_correcting_different_answers_do_not_clobber_the_total(
    client, db, graded_submission, monkeypatch
):
    """The submission row lock is what keeps `total_score` consistent.

    Both corrections recompute the total from the same set of answers, so
    without `FOR UPDATE` the second writer could read a stale set and
    overwrite the first writer's contribution. This pauses one writer
    mid-transaction, proves the other genuinely blocks behind it, then
    asserts the final total reflects *both* corrections.
    """
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from app.db.session import SessionLocal
    from app.services.authorization_service import AuthorizationService
    from app.services.history_service import HistoryService
    from app.schemas.history import GradeOverrideRequest
    from app.models.user import User
    from tests.test_authorization_concurrency import assert_future_is_blocked

    ctx = graded_submission
    first_ready = Event()
    release_first = Event()
    original_commit = AuthorizationService.commit_with_audit

    def paused_commit(session, **kwargs):
        first_ready.set()
        if not release_first.wait(timeout=5):
            raise RuntimeError("Timed out waiting to release the first reviewer")
        return original_commit(session, **kwargs)

    def correct(question_id, *, paused):
        with SessionLocal() as session:
            actor = session.get(User, ctx["teacher"]["id"])
            if paused:
                monkeypatch.setattr(
                    AuthorizationService, "commit_with_audit", paused_commit
                )
            else:
                monkeypatch.setattr(
                    AuthorizationService, "commit_with_audit", original_commit
                )
            HistoryService.override_answer_grade(
                session,
                uuid.UUID(ctx["submission_id"]),
                uuid.UUID(question_id),
                GradeOverrideRequest(points_awarded=10, reason="Cham lai"),
                actor,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(correct, ctx["questions"][0]["id"], paused=True)
        assert first_ready.wait(timeout=5)
        second = executor.submit(correct, ctx["questions"][1]["id"], paused=False)
        try:
            # The second reviewer cannot proceed while the first holds the row.
            assert_future_is_blocked(second)
        finally:
            release_first.set()
        first.result(timeout=10)
        second.result(timeout=10)

    db.expire_all()
    submission = db.get(Submission, uuid.UUID(ctx["submission_id"]))
    # Both corrections survived; neither overwrote the other.
    assert submission.total_score == 20.0
