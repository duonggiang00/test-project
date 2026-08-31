"""PostgreSQL integration coverage for the AI generation review queue
(AI-002) and the advisory grade-suggestion invariant (AI-009).

The invariant under test is a negative one: AI-authored content must not
reach `questions`/`flashcards`/`topic_briefs` except through an explicit
publish of an explicitly approved job. Every test here therefore asserts
row *counts* against the live tables at each step, not just the API
response, because a response saying "awaiting review" is worthless if a row
appeared anyway.

The provider is stubbed at the `AIProvider` boundary (the only external
boundary involved); everything else -- ownership scoping, row locking,
transitions, audit -- runs against real PostgreSQL, because that is where
the locking and constraint behavior actually lives.
"""

import uuid

import pytest
from sqlalchemy import func, select

from app.ai.provider import AIProviderError, GenerateResult, TokenUsage
from app.core.exceptions import AppException
from app.models.ai_generation import AIGenerationJob, AIGradeSuggestion
from app.models.audit_event import AuditEvent
from app.models.document_chunk import DocumentChunk
from app.models.exam import Exam, Option, Question
from app.models.flashcard import Flashcard, FlashcardDeck
from app.models.material import StudyMaterial
from app.models.submission import Submission, SubmissionAnswer
from app.models.topic import Topic
from app.models.topic_brief import TopicBrief
from app.models.user import User
from app.schemas.material import (
    GenerateFlashcardsRequest,
    GenerateQuestionsRequest,
)
from app.services.ai_generation_service import (
    AIGenerationService,
    AIGradeSuggestionService,
)
from app.services.material_service import MaterialService
from tests.test_authorization_idor import create_teacher, create_topic

QUESTIONS_RESPONSE = """[
  {"type": "MULTIPLE_CHOICE", "content": "What is the capital of France?",
   "points": 2, "difficulty": "EASY",
   "options": [{"content": "Paris", "is_correct": true},
               {"content": "Lyon", "is_correct": false}]},
  {"type": "MULTIPLE_CHOICE", "content": "Which ocean is largest?",
   "points": 3, "difficulty": "HARD",
   "options": [{"content": "Pacific", "is_correct": true},
               {"content": "Arctic", "is_correct": false}]}
]"""

FLASHCARDS_RESPONSE = """{"flashcards": [
  {"term": "Photosynthesis", "definition": "How plants convert light to energy."},
  {"term": "Mitosis", "definition": "Cell division producing two identical cells."}
]}"""

BRIEF_RESPONSE = '{"content": "# Study brief\\n\\nKey ideas from the material."}'


class StubProvider:
    """Deterministic stand-in for the external model call."""

    def __init__(self, *, text=None, error=None):
        self._text = text
        self._error = error

    def generate(self, request):
        if self._error is not None:
            raise self._error
        return GenerateResult(
            text=self._text,
            tool_calls=None,
            provider="stub",
            model=request.model,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            latency_ms=0.1,
            finish_reason="stop",
        )


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _material_with_chunk(db, owner_id, title="AI review material.txt"):
    material = StudyMaterial(
        uploader_id=owner_id,
        title=title,
        file_type="txt",
        file_path=f"uploads/materials/ai-review-{uuid.uuid4()}.txt",
        ai_status="completed",
    )
    db.add(material)
    db.flush()
    db.add(
        DocumentChunk(
            material_id=material.id,
            content="Paris is the capital of France. The Pacific is the largest ocean.",
            embedding=[0.0] * 1536,
        )
    )
    db.commit()
    db.refresh(material)
    return material


def _actor(db, owner):
    user = db.get(User, owner["id"])
    assert user is not None
    return user


def _generate(db, material, actor, *, flow="questions", text=QUESTIONS_RESPONSE):
    """Run one generation flow and return the resulting job id."""
    provider = StubProvider(text=text)
    if flow == "questions":
        result = MaterialService.generate_questions(
            db,
            material.id,
            GenerateQuestionsRequest(question_types=["MULTIPLE_CHOICE"], count=2),
            actor,
            provider=provider,
        )
    elif flow == "flashcards":
        result = MaterialService.generate_flashcards(
            db,
            material.id,
            GenerateFlashcardsRequest(count=2),
            actor,
            provider=provider,
        )
    else:
        result = MaterialService.generate_topic_brief(
            db, material.id, actor, provider=provider
        )
    assert result["status"] == "awaiting_review"
    return uuid.UUID(result["job_id"])


def _question_count(db, material_id):
    db.expire_all()
    return db.scalar(
        select(func.count(Question.id)).where(Question.material_id == material_id)
    )


def _job(db, job_id):
    db.expire_all()
    return db.get(AIGenerationJob, job_id)


def _transition_events(db, job_id, action=None):
    statement = select(AuditEvent).where(
        AuditEvent.entity_type == "ai_generation_job",
        AuditEvent.entity_id == str(job_id),
    )
    if action is not None:
        statement = statement.where(AuditEvent.action == action)
    return list(db.scalars(statement.order_by(AuditEvent.occurred_at)).all())


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_generated_questions_reach_the_live_table_only_after_approve_then_publish(
    client, db
):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))

    # Generation alone writes nothing publishable.
    assert _question_count(db, material.id) == 0
    job = _job(db, job_id)
    assert job.status == "awaiting_review"
    assert job.reviewer_id is None
    assert job.published_at is None

    listed = client.get(
        "/ai/generation-jobs?status=awaiting_review", headers=owner["headers"]
    )
    assert listed.status_code == 200
    assert str(job_id) in {item["id"] for item in listed.json()["items"]}

    detail = client.get(
        f"/ai/generation-jobs/{job_id}", headers=owner["headers"]
    )
    assert detail.status_code == 200
    assert len(detail.json()["draft_payload"]["questions"]) == 2

    # Publishing an unapproved job is refused by the allowlist, and writes
    # nothing on the way to being refused.
    early = client.post(
        f"/ai/generation-jobs/{job_id}/publish", headers=owner["headers"]
    )
    assert early.status_code == 409
    assert early.json()["error_code"] == "AI_JOB_INVALID_TRANSITION"
    assert _question_count(db, material.id) == 0

    approved = client.post(
        f"/ai/generation-jobs/{job_id}/approve", headers=owner["headers"]
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewer_id"] == str(owner["id"])
    # Approval is a decision, not a write.
    assert _question_count(db, material.id) == 0

    published = client.post(
        f"/ai/generation-jobs/{job_id}/publish", headers=owner["headers"]
    )
    assert published.status_code == 200
    body = published.json()
    assert body["status"] == "published"
    assert body["saved_count"] == 2

    db.expire_all()
    questions = list(
        db.scalars(
            select(Question).where(Question.material_id == material.id)
        ).all()
    )
    assert len(questions) == 2
    assert {q.content for q in questions} == {
        "What is the capital of France?",
        "Which ocean is largest?",
    }
    assert all(q.is_ai_generated for q in questions)
    assert all(q.owner_id == owner["id"] for q in questions)
    option_count = db.scalar(
        select(func.count(Option.id)).where(
            Option.question_id.in_([q.id for q in questions])
        )
    )
    assert option_count == 4

    final = _job(db, job_id)
    assert final.status == "published"
    assert final.published_at is not None


def test_publish_is_refused_directly_from_generated(client, db):
    """The spec's "No direct `generated -> published`" at the endpoint.

    The job never reaches `awaiting_review`, so nothing has been offered for
    review yet; publishing must be impossible rather than merely unimplemented.
    """
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    actor = _actor(db, owner)

    job = AIGenerationService.create_job(
        db,
        owner_id=owner["id"],
        material_id=material.id,
        use_case="question_generation",
    )
    AIGenerationService.commit_transition(db, job, "processing", actor=actor)
    AIGenerationService.commit_transition(
        db,
        job,
        "generated",
        actor=actor,
        draft_payload={
            "questions": [
                {
                    "type": "MULTIPLE_CHOICE",
                    "content": "Never published",
                    "options": [{"content": "A", "is_correct": True}],
                }
            ]
        },
    )
    job_id = job.id
    assert _job(db, job_id).status == "generated"

    response = client.post(
        f"/ai/generation-jobs/{job_id}/publish", headers=owner["headers"]
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "AI_JOB_INVALID_TRANSITION"

    # Approving straight from `generated` is refused too -- the only way in
    # is the `generated -> awaiting_review` step.
    approve = client.post(
        f"/ai/generation-jobs/{job_id}/approve", headers=owner["headers"]
    )
    assert approve.status_code == 409
    assert approve.json()["error_code"] == "AI_JOB_INVALID_TRANSITION"

    assert _question_count(db, material.id) == 0
    assert _job(db, job_id).status == "generated"


def test_reapproving_and_republishing_duplicate_nothing(client, db):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))

    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/approve", headers=owner["headers"]
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/publish", headers=owner["headers"]
        ).status_code
        == 200
    )
    assert _question_count(db, material.id) == 2
    settled = _job(db, job_id)
    version_after_publish = settled.version
    reviewer_after_publish = settled.reviewer_id

    # Every repeat is refused by the allowlist, not by a bespoke guard.
    for path in ("approve", "publish", "reject"):
        repeat = client.post(
            f"/ai/generation-jobs/{job_id}/{path}", headers=owner["headers"]
        )
        assert repeat.status_code == 409, path
        assert repeat.json()["error_code"] == "AI_JOB_INVALID_TRANSITION", path

    # No duplicate rows, and the terminal state is untouched.
    assert _question_count(db, material.id) == 2
    after = _job(db, job_id)
    assert after.status == "published"
    assert after.version == version_after_publish
    assert after.reviewer_id == reviewer_after_publish


def test_a_stale_reviewer_version_is_refused(client, db):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))
    stale_version = _job(db, job_id).version

    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/approve",
            json={"expected_version": stale_version},
            headers=owner["headers"],
        ).status_code
        == 200
    )

    # A second reviewer still holding the pre-approval version.
    conflict = client.post(
        f"/ai/generation-jobs/{job_id}/publish",
        json={"expected_version": stale_version},
        headers=owner["headers"],
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "AI_JOB_VERSION_CONFLICT"
    assert _question_count(db, material.id) == 0

    # The same call with the current version succeeds.
    current = _job(db, job_id).version
    ok = client.post(
        f"/ai/generation-jobs/{job_id}/publish",
        json={"expected_version": current},
        headers=owner["headers"],
    )
    assert ok.status_code == 200
    assert _question_count(db, material.id) == 2


def test_flashcards_and_topic_brief_publish_through_the_same_gate(client, db):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    actor = _actor(db, owner)

    deck_job = _generate(
        db, material, actor, flow="flashcards", text=FLASHCARDS_RESPONSE
    )
    brief_job = _generate(
        db, material, actor, flow="brief", text=BRIEF_RESPONSE
    )

    db.expire_all()
    assert db.scalar(
        select(func.count(FlashcardDeck.id)).where(
            FlashcardDeck.material_id == material.id
        )
    ) == 0
    assert db.scalar(
        select(func.count(TopicBrief.id)).where(
            TopicBrief.material_id == material.id
        )
    ) == 0

    for job_id in (deck_job, brief_job):
        assert (
            client.post(
                f"/ai/generation-jobs/{job_id}/approve", headers=owner["headers"]
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/ai/generation-jobs/{job_id}/publish",
                json={"title": "Reviewed output"},
                headers=owner["headers"],
            ).status_code
            == 200
        )

    db.expire_all()
    decks = list(
        db.scalars(
            select(FlashcardDeck).where(FlashcardDeck.material_id == material.id)
        ).all()
    )
    assert len(decks) == 1
    assert decks[0].title == "Reviewed output"
    assert db.scalar(
        select(func.count(Flashcard.id)).where(Flashcard.deck_id == decks[0].id)
    ) == 2

    briefs = list(
        db.scalars(
            select(TopicBrief).where(TopicBrief.material_id == material.id)
        ).all()
    )
    assert len(briefs) == 1
    assert briefs[0].is_ai_generated is True
    assert "Key ideas from the material." in briefs[0].content


def test_rejecting_a_job_closes_it_without_writing_anything(client, db):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))

    rejected = client.post(
        f"/ai/generation-jobs/{job_id}/reject", headers=owner["headers"]
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    publish = client.post(
        f"/ai/generation-jobs/{job_id}/publish", headers=owner["headers"]
    )
    assert publish.status_code == 409
    assert publish.json()["error_code"] == "AI_JOB_INVALID_TRANSITION"
    assert _question_count(db, material.id) == 0


def test_a_provider_failure_records_the_sanitized_code_and_publishes_nothing(
    client, db
):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    actor = _actor(db, owner)

    with pytest.raises(AppException) as excinfo:
        MaterialService.generate_questions(
            db,
            material.id,
            GenerateQuestionsRequest(question_types=["MULTIPLE_CHOICE"], count=2),
            actor,
            provider=StubProvider(error=AIProviderError("AI_TIMEOUT")),
        )
    assert excinfo.value.error_code == "AI_GENERATION_FAILED"

    db.expire_all()
    job = db.scalar(
        select(AIGenerationJob).where(
            AIGenerationJob.material_id == material.id
        )
    )
    assert job.status == "failed"
    assert job.failure_code == "AI_TIMEOUT"
    assert job.draft_payload is None
    assert _question_count(db, material.id) == 0

    # A failed job is terminal: it cannot be walked back into review.
    for path in ("approve", "publish"):
        response = client.post(
            f"/ai/generation-jobs/{job.id}/{path}", headers=owner["headers"]
        )
        assert response.status_code == 409
        assert response.json()["error_code"] == "AI_JOB_INVALID_TRANSITION"


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_review_authorization_across_the_five_actor_kinds(
    client, db, test_admin, test_student
):
    owner = create_teacher(client, db)
    intruder = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))
    missing_job_id = uuid.uuid4()

    # Anonymous: rejected before any ownership question is asked.
    anonymous = client.get(f"/ai/generation-jobs/{job_id}")
    assert anonymous.status_code == 401

    # Student: lacks the content permission entirely.
    student = client.get(
        f"/ai/generation-jobs/{job_id}", headers=test_student["headers"]
    )
    assert student.status_code == 403
    assert student.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"

    # Non-owner teacher: must not learn the job exists. The response for a
    # job owned by someone else and for a job id that never existed has to be
    # byte-identical apart from the request id.
    cross_owner = client.get(
        f"/ai/generation-jobs/{job_id}", headers=intruder["headers"]
    )
    absent = client.get(
        f"/ai/generation-jobs/{missing_job_id}", headers=intruder["headers"]
    )
    assert cross_owner.status_code == absent.status_code == 404
    assert cross_owner.json()["error_code"] == "AI_JOB_NOT_FOUND"
    assert {k: v for k, v in cross_owner.json().items() if k != "request_id"} == {
        k: v for k, v in absent.json().items() if k != "request_id"
    }

    # The same indistinguishability on every mutating route.
    for path in ("approve", "reject", "publish"):
        blocked = client.post(
            f"/ai/generation-jobs/{job_id}/{path}", headers=intruder["headers"]
        )
        nonexistent = client.post(
            f"/ai/generation-jobs/{missing_job_id}/{path}",
            headers=intruder["headers"],
        )
        assert blocked.status_code == nonexistent.status_code == 404, path
        assert blocked.json()["error_code"] == "AI_JOB_NOT_FOUND", path

    # A non-owner's list never contains it either.
    intruder_list = client.get(
        "/ai/generation-jobs", headers=intruder["headers"]
    )
    assert intruder_list.status_code == 200
    assert str(job_id) not in {
        item["id"] for item in intruder_list.json()["items"]
    }

    # Nothing above changed the job.
    assert _job(db, job_id).status == "awaiting_review"
    assert _question_count(db, material.id) == 0

    # Owner teacher and admin can both read it.
    assert (
        client.get(
            f"/ai/generation-jobs/{job_id}", headers=owner["headers"]
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/ai/generation-jobs/{job_id}", headers=test_admin["headers"]
        ).status_code
        == 200
    )


def test_an_admin_approving_a_teachers_job_is_recorded_as_the_reviewer(
    client, db, test_admin
):
    """The reviewer is the acting actor, never the generation actor.

    A teacher requested this content; an admin signed off on it. Recording
    the teacher as reviewer would make the audit trail claim the author
    approved their own draft.
    """
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))

    approved = client.post(
        f"/ai/generation-jobs/{job_id}/approve", headers=test_admin["headers"]
    )
    assert approved.status_code == 200

    job = _job(db, job_id)
    assert job.owner_id == owner["id"]
    assert job.reviewer_id == test_admin["id"]
    assert job.reviewer_id != job.owner_id
    assert job.reviewed_at is not None

    # The admin acting on someone else's resource is itself audited.
    override = db.scalar(
        select(AuditEvent).where(
            AuditEvent.action == "admin.override",
            AuditEvent.entity_type == "ai_generation_job",
            AuditEvent.entity_id == str(job_id),
        )
    )
    assert override is not None
    assert override.actor_id == test_admin["id"]
    assert override.owner_id == owner["id"]

    # And the published rows still belong to the content owner, not the admin.
    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/publish", headers=test_admin["headers"]
        ).status_code
        == 200
    )
    db.expire_all()
    owners = set(
        db.scalars(
            select(Question.owner_id).where(Question.material_id == material.id)
        ).all()
    )
    assert owners == {owner["id"]}


# ---------------------------------------------------------------------------
# Upload path
# ---------------------------------------------------------------------------


def test_uploading_a_material_creates_a_draft_not_questions(
    client, db, test_teacher, monkeypatch
):
    """The upload background task used to publish two questions outright."""
    response = client.post(
        "/materials/upload",
        files={"file": ("upload-gate.txt", b"Mock Document Content", "text/plain")},
        headers=test_teacher["headers"],
    )
    assert response.status_code == 200
    material_id = uuid.UUID(response.json()["id"])

    db.expire_all()
    assert _question_count(db, material_id) == 0

    job = db.scalar(
        select(AIGenerationJob).where(AIGenerationJob.material_id == material_id)
    )
    assert job is not None
    assert job.status == "awaiting_review"
    assert job.owner_id == test_teacher["id"]
    assert job.reviewer_id is None
    assert len(job.draft_payload["questions"]) == 2

    # The questions only exist once a human asks for them.
    assert (
        client.post(
            f"/ai/generation-jobs/{job.id}/approve",
            headers=test_teacher["headers"],
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/ai/generation-jobs/{job.id}/publish",
            headers=test_teacher["headers"],
        ).status_code
        == 200
    )
    assert _question_count(db, material_id) == 2


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def test_each_transition_emits_exactly_one_correctly_shaped_event(client, db):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))
    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/approve", headers=owner["headers"]
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/publish", headers=owner["headers"]
        ).status_code
        == 200
    )

    events = _transition_events(db, job_id)
    assert [event.action for event in events] == [
        "ai.generation.processing",
        "ai.generation.generated",
        "ai.generation.awaiting_review",
        "ai.generation.approved",
        "ai.generation.published",
    ]

    expected_pairs = [
        ("requested", "processing"),
        ("processing", "generated"),
        ("generated", "awaiting_review"),
        ("awaiting_review", "approved"),
        ("approved", "published"),
    ]
    for event, (before, after) in zip(events, expected_pairs):
        assert event.outcome == "success"
        assert event.owner_id == owner["id"]
        assert event.actor_id == owner["id"]
        assert event.actor_role == "teacher"
        assert event.changes == {"status": {"before": before, "after": after}}
        # `use_case` is on every transition; AI-003 adds the
        # `ERROR_AND_AUDIT_CONTRACTS.md` §2.4 fields that are knowable at
        # each particular point, so the exact metadata shape is asserted
        # per-action below rather than as one fixed dict.
        assert event.event_metadata["use_case"] == "question_generation"
        assert event.request_id

    # AI-003: each action carries exactly the §2.4 fields knowable at that
    # point -- the call's identity once the prompt is rendered, the usage
    # and cost once the provider answers, and the reviewer once a human
    # decides. The raw prompt and raw output are in neither: they live only
    # in `ai_restricted_payloads`, referenced here by id.
    by_action = {event.action: event.event_metadata for event in events}

    processing = by_action["ai.generation.processing"]
    assert processing["prompt_version"] == "question_generation-v3"
    assert processing["provider"] == "openrouter"
    assert processing["model"]
    assert processing["context_source_ids"]

    generated = by_action["ai.generation.generated"]
    assert generated["prompt_version"] == "question_generation-v3"
    assert "input_tokens" in generated
    assert "output_tokens" in generated
    # Honest when unpriced: no `AI_TOKEN_PRICING` entry means an explicit
    # null, never a fabricated figure.
    assert "estimated_cost" in generated
    assert isinstance(generated["latency_ms"], int)
    assert generated["restricted_payload_id"]

    approved = by_action["ai.generation.approved"]
    assert approved["reviewer_id"] == str(owner["id"])
    assert approved["review_outcome"] == "approved"

    # No rejected/failed event was emitted along a clean path.
    assert _transition_events(db, job_id, "ai.generation.rejected") == []
    assert _transition_events(db, job_id, "ai.generation.failed") == []


def test_a_refused_transition_emits_no_audit_event(client, db):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    job_id = _generate(db, material, _actor(db, owner))
    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/approve", headers=owner["headers"]
        ).status_code
        == 200
    )
    before = len(_transition_events(db, job_id))

    # Refused by the allowlist.
    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/reject", headers=owner["headers"]
        ).status_code
        == 409
    )
    # Refused by optimistic concurrency.
    assert (
        client.post(
            f"/ai/generation-jobs/{job_id}/publish",
            json={"expected_version": 1},
            headers=owner["headers"],
        ).status_code
        == 409
    )
    assert len(_transition_events(db, job_id)) == before


def test_a_rolled_back_publish_writes_neither_rows_nor_an_event(client, db):
    """A publish that fails part-way through must leave no trace.

    The rows and the `published` transition share one transaction, so an
    unusable draft discovered during publication rolls back both -- the job
    stays `approved` and re-publishable once the draft is fixed, rather than
    ending up marked published with nothing published.
    """
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    actor = _actor(db, owner)

    job = AIGenerationService.create_job(
        db,
        owner_id=owner["id"],
        material_id=material.id,
        use_case="question_generation",
    )
    AIGenerationService.commit_transition(db, job, "processing", actor=actor)
    # A draft the model produced but which cannot become a Question row.
    AIGenerationService.commit_transition(
        db,
        job,
        "generated",
        actor=actor,
        draft_payload={"questions": [{"points": "not a number"}]},
    )
    AIGenerationService.commit_transition(db, job, "awaiting_review", actor=actor)
    AIGenerationService.commit_transition(db, job, "approved", actor=actor)
    job_id = job.id
    before = len(_transition_events(db, job_id))

    response = client.post(
        f"/ai/generation-jobs/{job_id}/publish", headers=owner["headers"]
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "AI_DRAFT_INVALID"

    assert _question_count(db, material.id) == 0
    assert _transition_events(db, job_id, "ai.generation.published") == []
    assert len(_transition_events(db, job_id)) == before
    assert _job(db, job_id).status == "approved"


def test_publish_rejects_fill_draft_with_mismatched_blank_contract(client, db):
    owner = create_teacher(client, db)
    material = _material_with_chunk(db, owner["id"])
    actor = _actor(db, owner)
    job = AIGenerationService.create_job(
        db,
        owner_id=owner["id"],
        material_id=material.id,
        use_case="question_generation",
    )
    AIGenerationService.commit_transition(db, job, "processing", actor=actor)
    AIGenerationService.commit_transition(
        db,
        job,
        "generated",
        actor=actor,
        draft_payload={
            "questions": [
                {
                    "type": "FILL_IN_BLANK",
                    "content": "This draft has no canonical token.",
                    "metadata_json": {
                        "blanks": [
                            {
                                "blank_index": 0,
                                "acceptable_answers": ["answer"],
                            }
                        ]
                    },
                }
            ]
        },
    )
    AIGenerationService.commit_transition(db, job, "awaiting_review", actor=actor)
    AIGenerationService.commit_transition(db, job, "approved", actor=actor)

    response = client.post(
        f"/ai/generation-jobs/{job.id}/publish",
        headers=owner["headers"],
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "AI_DRAFT_INVALID"
    assert _question_count(db, material.id) == 0
    assert _job(db, job.id).status == "approved"


# ---------------------------------------------------------------------------
# AI-009: advisory grade suggestions
# ---------------------------------------------------------------------------


def test_creating_a_grade_suggestion_changes_no_awarded_points(
    client, db, test_student
):
    """An AI grade suggestion is advice, never a grade.

    Creating one must not touch `points_awarded`, `is_correct`, or the
    submission total: only an explicit approval may ever apply it, and no
    apply path exists yet.
    """
    owner = create_teacher(client, db)
    exam = Exam(
        creator_id=owner["id"],
        title=f"Advisory grading exam {uuid.uuid4()}",
        duration_minutes=30,
        is_published=True,
    )
    db.add(exam)
    db.flush()
    question = Question(
        owner_id=owner["id"],
        exam_id=exam.id,
        content="Explain the water cycle.",
        points=10,
    )
    db.add(question)
    db.flush()
    submission = Submission(
        exam_id=exam.id,
        student_id=uuid.UUID(test_student["id"]),
        total_score=4.0,
        status="graded",
    )
    db.add(submission)
    db.flush()
    answer = SubmissionAnswer(
        submission_id=submission.id,
        question_id=question.id,
        answer_data={"text": "Evaporation, condensation, precipitation."},
        is_correct=False,
        points_awarded=4.0,
    )
    db.add(answer)
    db.commit()

    suggestion = AIGradeSuggestionService.create_suggestion(
        db,
        submission_answer_id=answer.id,
        owner_id=owner["id"],
        suggested_points=9,
    )
    db.commit()

    db.expire_all()
    stored = db.get(AIGradeSuggestion, suggestion.id)
    assert stored.status == "awaiting_review"
    assert stored.suggested_points == 9
    assert stored.reviewer_id is None
    assert stored.applied_at is None

    # The graded record is exactly as the deterministic grader left it.
    reloaded_answer = db.get(SubmissionAnswer, answer.id)
    assert reloaded_answer.points_awarded == 4.0
    assert reloaded_answer.is_correct is False
    reloaded_submission = db.get(Submission, submission.id)
    assert reloaded_submission.total_score == 4.0
    assert reloaded_submission.status == "graded"


def test_generating_a_topic_kit_creates_drafts_not_live_content(
    client, db, test_teacher, monkeypatch
):
    """`generate-topic-kit` used to publish a brief and a deck outright.

    Independent review of Milestone 9 found this second background worker
    still writing `topic.brief_content`/`brief_ai_generated` and adding a
    `FlashcardDeck` with its `Flashcard` rows directly -- an auto-publish
    escape that `CANONICAL_PROJECT_SPEC.md` 9.2 and ADR-0006 both forbid,
    and that AI-002's own acceptance criterion rules out.
    """
    material = _material_with_chunk(db, test_teacher["id"])
    topic = create_topic(client, test_teacher, f"Topic kit {uuid.uuid4()}")
    topic_id = uuid.UUID(topic["id"])

    response = client.post(
        "/flashcards/ai/generate-topic-kit",
        json={"material_id": str(material.id), "topic_id": str(topic_id)},
        headers=test_teacher["headers"],
    )
    assert response.status_code == 200

    db.expire_all()

    # Nothing reached a live table.
    assert db.scalar(
        select(func.count())
        .select_from(FlashcardDeck)
        .where(FlashcardDeck.material_id == material.id)
    ) == 0
    assert db.scalar(
        select(func.count())
        .select_from(TopicBrief)
        .where(TopicBrief.material_id == material.id)
    ) == 0
    refreshed_topic = db.get(Topic, topic_id)
    assert not refreshed_topic.brief_content
    assert not refreshed_topic.brief_ai_generated

    # Both halves of the kit are waiting for a human instead.
    jobs = db.scalars(
        select(AIGenerationJob).where(AIGenerationJob.material_id == material.id)
    ).all()
    by_use_case = {job.use_case: job for job in jobs}
    assert set(by_use_case) == {
        "topic_brief_generation",
        "flashcard_generation",
    }
    for job in by_use_case.values():
        assert job.status == "awaiting_review"
        assert job.owner_id == test_teacher["id"]
        assert job.reviewer_id is None

    assert by_use_case["topic_brief_generation"].draft_payload["content"]
    assert len(by_use_case["flashcard_generation"].draft_payload["flashcards"]) == 3

    # And the content only becomes real once a human approves and publishes.
    brief_job = by_use_case["topic_brief_generation"]
    assert (
        client.post(
            f"/ai/generation-jobs/{brief_job.id}/approve",
            headers=test_teacher["headers"],
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/ai/generation-jobs/{brief_job.id}/publish",
            json={"topic_id": str(topic_id)},
            headers=test_teacher["headers"],
        ).status_code
        == 200
    )
    db.expire_all()
    assert db.scalar(
        select(func.count())
        .select_from(TopicBrief)
        .where(TopicBrief.material_id == material.id)
    ) == 1
