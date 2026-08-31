# RAG-SEMANTIC-001 Handoff

Status: REVIEW
Risk: L3 (retrieval, migration, and breaking legacy route removal)
Branch: `codex/rag-semantic-001`

## Delivered

- Typed OpenRouter embedding boundary with fixed 1536-dimension validation.
- One batched embedding request for uploaded document chunks; empty documents
  avoid a provider call.
- Real SQLAlchemy `Vector(1536)` mapping; the previous Vector-to-VARCHAR
  compiler override is removed.
- Fail-closed pgvector extension creation, vector conversion, HNSW cosine index,
  PostgreSQL simple-text FTS index, and migration-runner schema assertions.
- Owner/material-scoped lexical and hybrid retrieval with bounded candidates,
  reciprocal-rank fusion, deterministic tie-breaking, and lexical rollback.
- Sanitized chat `sources` SSE event and audited `retrieval_mode`.
- Removed the approved compatibility-only `/ai/process-document` route, schemas,
  service path, and call-site tests; regenerated OpenAPI and inventory.
- Added deterministic retrieval metrics/reporting without raw source content.
- Added a sanitized production-service evaluation CLI with material-scoped query
  counts and bounded embedding ingestion/index validation.
- Retrieval reports are bound to the approved AI-006 fingerprint, all 16 RAG
  cases, canonical-source-to-chunk mappings, and fixed quality floors.
- CI PostgreSQL service images aligned to `pgvector/pgvector:0.8.6-pg18`.

## Verification

- Focused retrieval/ingestion/evaluator/chat tests: 35 passed.
- Backend unit + contract: 500 passed.
- Ruff: passed for `app`, `scripts`, and `tests`.
- Targeted Mypy: passed for provider, retrieval, evaluator, migration, and test
  database modules.
- Fast manifest: `reports/agent-workflow/rag-semantic-001-final-3/fast.json`, 13/13.
- OpenAPI, inventory, and database-model drift checks pass.
- Migration runner stops fail-closed because local PostgreSQL 18.6 does not have
  the `vector` extension installed; the temporary test database is dropped.

## Remaining before DONE

1. Run migration roundtrip and PostgreSQL integration on PostgreSQL 18 with
   pgvector 0.8.6 (CI image is configured).
2. Run the approved retrieval evaluation with the owner-approved dataset and
   attach sanitized metrics/report artifacts.
3. Complete independent L3 review and reconcile any findings.
4. Keep `RAG_RETRIEVAL_MODE=lexical` until semantic thresholds are separately
   approved; do not enable AI-008 CI thresholds in this change.

## Rollback

Set `RAG_RETRIEVAL_MODE=lexical` for runtime rollback or `RAG_ENABLED=false` to
disable material chat. The migration downgrade removes only the RAG indexes
and restores the exact pre-migration `vector(1536)` schema without dropping the
shared extension.
