"""Regression tests for MaterialService's AI generation flows (AI-001/AI-002).

`generate_questions`/`generate_flashcards`/`generate_topic_brief` had no
existing test coverage before the AI-001 refactor (verified: no test in this
repo exercised `material_service.py`'s module-level `OpenAI` client). These
tests establish that coverage against the provider abstraction: the LLM
response is mocked at the `AIProvider` boundary (matching this test
directory's convention of mocking only the external boundary under test --
see `test_material_storage_service.py`), so the assertions are exact and
deterministic rather than depending on a real model's output.

AI-002 changed what `generate_*` *produces*: a reviewable `AIGenerationJob`
draft instead of an unsaved preview. The provider-boundary assertions below
are unchanged; the added assertions pin the resulting job state, including
the ordering guarantee that matters most -- the provider call happens
between two committed transactions, never inside one.
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai.provider import AIProviderError, GenerateResult, TokenUsage
from app.core.exceptions import AppException
from app.models.ai_generation import AIGenerationJob
from app.models.document_chunk import DocumentChunk
from app.models.material import StudyMaterial
from app.schemas.material import GenerateFlashcardsRequest, GenerateQuestionsRequest
from app.services.material_service import MaterialService


class _ScalarsResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeSession:
    """Fake session for the AI-generation call path.

    Ignores the compiled `select()` statement and always returns the canned
    material/chunks -- ownership-scoping SQL itself is covered by
    `test_authorization_policy.py` and the PostgreSQL integration suite.
    `commit` only needs to be a counter here because the test actor owns the
    material outright, so the admin-override audit branch is never reached
    (see `AuthorizationService`).

    `flush` assigns primary keys the way the real session does at flush
    time, because the audit event recorded with each transition references
    `job.id`.
    """

    def __init__(self, material, chunks):
        self._material = material
        self._chunks = chunks
        self.commit_calls = 0
        self.added = []

    def scalar(self, statement):
        return self._material

    def scalars(self, statement):
        return _ScalarsResult(self._chunks)

    def add(self, instance):
        self.added.append(instance)

    def flush(self):
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = uuid4()

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        raise AssertionError("generate_* must not roll back a fake session")

    @property
    def job(self) -> AIGenerationJob:
        jobs = [item for item in self.added if isinstance(item, AIGenerationJob)]
        assert len(jobs) == 1, f"expected exactly one job, got {len(jobs)}"
        return jobs[0]


class FakeProvider:
    """Deterministic stand-in for `AIProvider.generate`.

    Also snapshots the session state at call time so a test can prove the
    change contract's "provider calls occur outside long database
    transactions": when `generate` runs, the request/`processing`
    transaction must already be committed and nothing else pending.
    """

    def __init__(
        self,
        *,
        text: str | None = None,
        error: AIProviderError | None = None,
        session: FakeSession | None = None,
    ):
        self._text = text
        self._error = error
        self._session = session
        self.received_requests = []
        self.commits_before_call = None
        self.job_status_at_call = None

    def generate(self, request):
        self.received_requests.append(request)
        if self._session is not None:
            self.commits_before_call = self._session.commit_calls
            self.job_status_at_call = self._session.job.status
        if self._error is not None:
            raise self._error
        return GenerateResult(
            text=self._text,
            tool_calls=None,
            provider="fake",
            model=request.model,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            latency_ms=0.1,
            finish_reason="stop",
        )


def _owner_and_material():
    owner_id = uuid4()
    owner = SimpleNamespace(id=owner_id, role="teacher")
    material = StudyMaterial(
        id=uuid4(),
        uploader_id=owner_id,
        title="Sample Material",
        file_type="pdf",
        file_path="uploads/materials/sample.pdf",
    )
    chunk = DocumentChunk(
        material_id=material.id,
        content="Nội dung mẫu.",
        embedding=[0.0] * 1536,
    )
    return owner, material, [chunk]


@pytest.mark.unit
def test_generate_questions_parks_the_providers_parsed_json_in_a_reviewable_job():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(
        text='[{"type": "SINGLE_CHOICE", "content": "q1"}]', session=db
    )

    result = MaterialService.generate_questions(
        db,
        material.id,
        GenerateQuestionsRequest(question_types=["SINGLE_CHOICE"], count=1, difficulty="EASY"),
        owner,
        provider=provider,
    )

    job = db.job
    assert result == {
        "job_id": str(job.id),
        "status": "awaiting_review",
        "questions": [{"type": "SINGLE_CHOICE", "content": "q1"}],
    }
    # The draft stops at review; nothing here writes a Question row.
    assert job.status == "awaiting_review"
    assert job.use_case == "question_generation"
    assert job.owner_id == material.uploader_id
    assert job.reviewer_id is None
    assert job.draft_payload == {
        "questions": [{"type": "SINGLE_CHOICE", "content": "q1"}]
    }
    # processing, generated, awaiting_review -- one commit each.
    assert db.commit_calls == 3
    # The provider ran after the `processing` transaction committed.
    assert provider.commits_before_call == 1
    assert provider.job_status_at_call == "processing"

    sent_request = provider.received_requests[0]
    assert sent_request.model == "meta-llama/llama-3.1-8b-instruct"
    assert sent_request.temperature == 0.7
    assert "Nội dung mẫu." in sent_request.messages[0]["content"]


@pytest.mark.unit
def test_generate_questions_strips_a_markdown_fence_identically_to_the_pre_refactor_logic():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(text='Sure:\n```json\n[{"type": "MATCHING"}]\n```')

    result = MaterialService.generate_questions(
        db,
        material.id,
        GenerateQuestionsRequest(question_types=["MATCHING"], count=1),
        owner,
        provider=provider,
    )

    assert result["questions"] == [{"type": "MATCHING"}]


@pytest.mark.unit
def test_generate_questions_maps_a_malformed_json_response_to_ai_parse_error():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(text="not JSON at all")

    with pytest.raises(AppException) as excinfo:
        MaterialService.generate_questions(
            db,
            material.id,
            GenerateQuestionsRequest(question_types=["SINGLE_CHOICE"]),
            owner,
            provider=provider,
        )

    assert excinfo.value.error_code == "AI_PARSE_ERROR"
    assert excinfo.value.status_code == 500
    # The response body still carries no raw parser text.
    assert excinfo.value.message in (None, "")
    # An unparseable response leaves a terminal `failed` job rather than one
    # stuck in `processing` forever.
    assert db.job.status == "failed"
    assert db.job.failure_code == "AI_PARSE_ERROR"
    assert db.job.draft_payload is None
    assert db.commit_calls == 2


@pytest.mark.unit
def test_generate_questions_records_the_sanitized_provider_error_code_on_the_failed_job():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(error=AIProviderError("AI_RATE_LIMIT_EXCEEDED"))

    with pytest.raises(AppException) as excinfo:
        MaterialService.generate_questions(
            db,
            material.id,
            GenerateQuestionsRequest(question_types=["SINGLE_CHOICE"]),
            owner,
            provider=provider,
        )

    # Historical behavior (unchanged): any provider-call failure surfaces as
    # the single fixed AI_GENERATION_FAILED code, regardless of cause.
    assert excinfo.value.error_code == "AI_GENERATION_FAILED"
    # The specific cause is retained on the job, not leaked to the client.
    # `AIProviderError.error_code` is sanitized by the provider layer.
    assert db.job.status == "failed"
    assert db.job.failure_code == "AI_RATE_LIMIT_EXCEEDED"
    assert db.commit_calls == 2


@pytest.mark.unit
def test_generate_flashcards_returns_the_providers_parsed_flashcards():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(
        text='{"flashcards": [{"term": "AI", "definition": "Tri tue nhan tao"}]}'
    )

    result = MaterialService.generate_flashcards(
        db,
        material.id,
        GenerateFlashcardsRequest(count=1),
        owner,
        provider=provider,
    )

    assert result["flashcards"] == [{"term": "AI", "definition": "Tri tue nhan tao"}]
    assert result["status"] == "awaiting_review"
    assert db.job.use_case == "flashcard_generation"
    assert provider.received_requests[0].temperature == 0.5


@pytest.mark.unit
def test_generate_flashcards_maps_a_malformed_json_response_to_ai_parse_error():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(text="not JSON")

    with pytest.raises(AppException) as excinfo:
        MaterialService.generate_flashcards(
            db,
            material.id,
            GenerateFlashcardsRequest(count=1),
            owner,
            provider=provider,
        )

    assert excinfo.value.error_code == "AI_PARSE_ERROR"


@pytest.mark.unit
def test_generate_topic_brief_returns_the_providers_parsed_content():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(text='{"content": "# Tom tat"}')

    result = MaterialService.generate_topic_brief(
        db,
        material.id,
        owner,
        provider=provider,
    )

    assert result["content"] == "# Tom tat"
    assert result["status"] == "awaiting_review"
    assert db.job.use_case == "topic_brief_generation"
    assert provider.received_requests[0].temperature == 0.5


@pytest.mark.unit
def test_generate_topic_brief_maps_a_provider_failure_to_ai_generation_failed():
    owner, material, chunks = _owner_and_material()
    db = FakeSession(material, chunks)
    provider = FakeProvider(error=AIProviderError("AI_TIMEOUT"))

    with pytest.raises(AppException) as excinfo:
        MaterialService.generate_topic_brief(
            db,
            material.id,
            owner,
            provider=provider,
        )

    assert excinfo.value.error_code == "AI_GENERATION_FAILED"
