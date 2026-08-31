from uuid import UUID, uuid4

import pytest

from app.models.document_chunk import DocumentChunk
from app.services.rag_retrieval_service import RagRetrievalService


class _Scalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.statements = []

    def scalars(self, statement):
        self.statements.append(statement)
        return _Scalars(self.responses.pop(0))


class FakeEmbeddingProvider:
    def __init__(self):
        self.requests = []

    def embed(self, request):
        self.requests.append(request)
        return type("EmbeddingResult", (), {"embeddings": [[0.1] * 1536]})()


def _chunk(material_id, content):
    return DocumentChunk(id=uuid4(), material_id=material_id, content=content, embedding=[0.0] * 1536)


@pytest.mark.unit
def test_lexical_retrieval_is_material_scoped_and_does_not_call_embeddings():
    material_id = uuid4()
    chunk = _chunk(material_id, "PostgreSQL vector search")
    db = FakeSession([chunk])
    provider = FakeEmbeddingProvider()

    result = RagRetrievalService.retrieve(
        db, material_id=material_id, query="vector", mode="lexical", embedding_provider=provider
    )

    assert [item.chunk for item in result] == [chunk]
    assert provider.requests == []
    assert "document_chunks.material_id" in str(db.statements[0])
    assert "to_tsvector" in str(db.statements[0])


@pytest.mark.unit
def test_lexical_retrieval_rolls_back_to_latest_chunks_for_no_query():
    material_id = uuid4()
    chunk = _chunk(material_id, "latest")
    db = FakeSession([chunk])

    result = RagRetrievalService.retrieve(db, material_id=material_id, query=" ", mode="lexical")

    assert result[0].chunk is chunk
    assert len(db.statements) == 1
    assert "ORDER BY document_chunks.id DESC" in str(db.statements[0])


@pytest.mark.unit
def test_hybrid_retrieval_fuses_ranks_and_calls_embedding_once():
    material_id = uuid4()
    lexical = _chunk(material_id, "lexical")
    shared = _chunk(material_id, "shared")
    semantic = _chunk(material_id, "semantic")
    db = FakeSession([lexical, shared], [shared, semantic])
    provider = FakeEmbeddingProvider()

    result = RagRetrievalService.retrieve(
        db, material_id=material_id, query="meaning", mode="hybrid", embedding_provider=provider
    )

    assert result[0].chunk is shared
    assert result[0].lexical_rank == 2
    assert result[0].semantic_rank == 1
    assert provider.requests[0].input_type == "search_query"
    assert len(provider.requests) == 1
    assert len(db.statements) == 2


@pytest.mark.unit
def test_invalid_retrieval_mode_fails_closed_before_database_access():
    db = FakeSession()
    with pytest.raises(ValueError, match="invalid retrieval mode"):
        RagRetrievalService.retrieve(db, material_id=UUID(int=0), query="x", mode="unsafe")
    assert db.statements == []
