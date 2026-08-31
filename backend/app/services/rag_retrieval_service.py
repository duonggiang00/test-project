"""Owner-scoped lexical and hybrid retrieval for material chat."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.ai import default_embedding_provider
from app.ai.provider import EmbeddingProvider, EmbeddingRequest
from app.core.config import settings
from app.models.document_chunk import DocumentChunk


_RRF_K = 60
_DEFAULT_LIMIT = 3
_CANDIDATE_LIMIT = 8


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk plus non-sensitive ranking metadata."""

    chunk: DocumentChunk
    score: float
    lexical_rank: int | None = None
    semantic_rank: int | None = None


class RagRetrievalService:
    """Execute bounded, material-scoped retrieval without query-per-row work."""

    @staticmethod
    def retrieve(
        db: Session,
        *,
        material_id: UUID,
        query: str,
        mode: str | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[RetrievedChunk]:
        retrieval_mode = mode or settings.RAG_RETRIEVAL_MODE
        if retrieval_mode not in {"lexical", "hybrid"}:
            raise ValueError("invalid retrieval mode")
        bounded_limit = max(1, min(limit, 10))
        normalized_query = query.strip()
        if not normalized_query:
            return RagRetrievalService._latest(db, material_id, bounded_limit)

        lexical = RagRetrievalService._lexical(
            db, material_id, normalized_query, _CANDIDATE_LIMIT
        )
        if retrieval_mode == "lexical":
            if not lexical:
                return RagRetrievalService._latest(db, material_id, bounded_limit)
            return [
                RetrievedChunk(chunk=chunk, score=1 / (_RRF_K + rank), lexical_rank=rank)
                for rank, chunk in enumerate(lexical, start=1)
            ][:bounded_limit]

        provider = embedding_provider or default_embedding_provider
        embedding_result = provider.embed(
            EmbeddingRequest(
                inputs=(normalized_query,),
                model=settings.AI_EMBEDDING_MODEL,
                dimensions=settings.AI_EMBEDDING_DIMENSIONS,
                input_type="search_query",
            )
        )
        semantic = RagRetrievalService._semantic(
            db,
            material_id,
            embedding_result.embeddings[0],
            _CANDIDATE_LIMIT,
        )
        return RagRetrievalService._fuse(lexical, semantic, bounded_limit)

    @staticmethod
    def _lexical(
        db: Session,
        material_id: UUID,
        query: str,
        limit: int,
    ) -> list[DocumentChunk]:
        ts_query = func.plainto_tsquery("simple", query)
        ts_vector = func.to_tsvector("simple", DocumentChunk.content)
        score = func.ts_rank_cd(ts_vector, ts_query)
        statement: Select[tuple[DocumentChunk, float]] = (
            select(DocumentChunk, score.label("score"))
            .where(
                DocumentChunk.material_id == material_id,
                ts_vector.op("@@")(ts_query),
            )
            .order_by(score.desc(), DocumentChunk.id.asc())
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def _semantic(
        db: Session,
        material_id: UUID,
        embedding: list[float],
        limit: int,
    ) -> list[DocumentChunk]:
        distance = DocumentChunk.embedding.cosine_distance(embedding)
        statement = (
            select(DocumentChunk, distance.label("distance"))
            .where(
                DocumentChunk.material_id == material_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance.asc(), DocumentChunk.id.asc())
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def _latest(db: Session, material_id: UUID, limit: int) -> list[RetrievedChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.material_id == material_id)
            .order_by(DocumentChunk.id.desc())
            .limit(limit)
        )
        chunks = list(db.scalars(statement).all())
        return [
            RetrievedChunk(chunk=chunk, score=1 / (_RRF_K + rank), lexical_rank=rank)
            for rank, chunk in enumerate(chunks, start=1)
        ]

    @staticmethod
    def _fuse(
        lexical: list[DocumentChunk],
        semantic: list[DocumentChunk],
        limit: int,
    ) -> list[RetrievedChunk]:
        fused: dict[str, RetrievedChunk] = {}
        for rank, chunk in enumerate(lexical, start=1):
            if chunk.id is None:
                continue
            chunk_key = str(chunk.id)
            fused[chunk_key] = RetrievedChunk(
                chunk=chunk,
                score=1 / (_RRF_K + rank),
                lexical_rank=rank,
            )
        for rank, chunk in enumerate(semantic, start=1):
            if chunk.id is None:
                continue
            chunk_key = str(chunk.id)
            existing = fused.get(chunk_key)
            semantic_score = 1 / (_RRF_K + rank)
            if existing is None:
                fused[chunk_key] = RetrievedChunk(
                    chunk=chunk,
                    score=semantic_score,
                    semantic_rank=rank,
                )
            else:
                fused[chunk_key] = RetrievedChunk(
                    chunk=existing.chunk,
                    score=existing.score + semantic_score,
                    lexical_rank=existing.lexical_rank,
                    semantic_rank=rank,
                )
        return sorted(
            fused.values(),
            key=lambda item: (-item.score, str(item.chunk.id)),
        )[:limit]
