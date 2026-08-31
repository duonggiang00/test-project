from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai.provider import EmbeddingResult
from app.services import ai_service


class FakeSession:
    def __init__(self, material, actor):
        self.material = material
        self.actor = actor
        self.persisted = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def scalar(self, statement):
        return self.material

    def add_all(self, items):
        self.persisted.extend(items)

    def get(self, model, identifier):
        return self.actor

    def commit(self):
        self.commits += 1


class FakeEmbeddingProvider:
    def __init__(self):
        self.requests = []

    def embed(self, request):
        self.requests.append(request)
        return EmbeddingResult(
            embeddings=[[0.1] * request.dimensions for _ in request.inputs],
            provider="fake",
            model=request.model,
            input_tokens=3,
            latency_ms=1.0,
        )


@pytest.mark.unit
def test_uploaded_document_chunks_are_embedded_in_one_batch(monkeypatch):
    material_id = uuid4()
    owner_id = uuid4()
    material = SimpleNamespace(
        id=material_id,
        uploader_id=owner_id,
        title="Material",
        file_path="uploads/material.txt",
        parsed_text=None,
        ai_status="pending",
    )
    actor = SimpleNamespace(id=owner_id, role="teacher")
    db = FakeSession(material, actor)
    provider = FakeEmbeddingProvider()
    parked = []

    monkeypatch.setattr(ai_service, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        ai_service,
        "extract_and_chunk_material",
        lambda path: ("full text", ["first chunk", "second chunk"]),
    )
    monkeypatch.setattr(
        ai_service,
        "_park_draft_for_review",
        lambda *args, **kwargs: parked.append(kwargs),
    )

    ai_service.process_document_and_generate_questions(
        str(material_id), str(owner_id), "request-1", embedding_provider=provider
    )

    assert len(provider.requests) == 1
    assert provider.requests[0].inputs == ("first chunk", "second chunk")
    assert provider.requests[0].input_type == "search_document"
    assert [chunk.content for chunk in db.persisted] == ["first chunk", "second chunk"]
    assert all(len(chunk.embedding) == 1536 for chunk in db.persisted)
    assert material.parsed_text == "full text"
    assert parked and parked[0]["use_case"] == "question_generation"


@pytest.mark.unit
def test_oversized_document_batch_fails_before_provider_call(monkeypatch):
    material_id = uuid4()
    owner_id = uuid4()
    material = SimpleNamespace(
        id=material_id,
        uploader_id=owner_id,
        title="Material",
        file_path="uploads/material.txt",
        parsed_text=None,
        ai_status="pending",
    )
    actor = SimpleNamespace(id=owner_id, role="teacher")
    db = FakeSession(material, actor)
    provider = FakeEmbeddingProvider()
    monkeypatch.setattr(ai_service, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        ai_service,
        "extract_and_chunk_material",
        lambda path: ("full text", [f"chunk-{index}" for index in range(65)]),
    )

    ai_service.process_document_and_generate_questions(
        str(material_id), str(owner_id), "request-oversized", embedding_provider=provider
    )

    assert provider.requests == []
    assert material.ai_status == "failed"
