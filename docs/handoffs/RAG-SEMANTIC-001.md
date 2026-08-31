# RAG-SEMANTIC-001 Handoff

Status: DONE
Risk: L3 (retrieval, migration, and breaking legacy route removal)
Branch: `codex/rag-semantic-001-ci`

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
- Added an isolated campaign runner that creates 16 deterministic materials
  with one canonical source and three same-material distractors, batches all 64
  document embeddings once, caps the complete campaign at 17 requests/80
  inputs, pins OpenRouter to OpenAI with zero retries and no fallback, writes
  create-only sanitized evidence, and always drops its test database.
- Accepted OpenRouter's exact provider-prefix normalization for embedding
  response metadata while continuing to reject unrelated model identifiers.
- Fixed CI parsing of the fixed 1536-dimension policy and preserved rejection
  of every other dimension.
- Retrieval reports are bound to the approved AI-006 fingerprint, all 16 RAG
  cases, canonical-source-to-chunk mappings, and fixed quality floors.
- CI PostgreSQL service images aligned to `pgvector/pgvector:0.8.6-pg18`.

## Verification

| Evidence | Result |
|---|---|
| Focused provider/config/retrieval tests | 41 passed; Ruff and Mypy passed |
| Backend manifest | 486 unit, 23 contract, 170 PostgreSQL integration passed; `reports/agent-workflow/rag-semantic-001-final-3/backend.json` |
| Migration manifest | PostgreSQL 18/pgvector 0.8.6 upgrade/downgrade/upgrade passed; `reports/agent-workflow/rag-semantic-001-migration-final/migration.json` |
| Coverage manifest | 170 backend integration and 182 frontend tests plus coverage policy passed; `reports/agent-workflow/rag-semantic-001-coverage-final/coverage.json` |
| Mocked E2E manifest | 28/28 passed across Chromium, Firefox, WebKit, and mobile Chrome; `reports/agent-workflow/rag-semantic-001-e2e-mocked-final-3/e2e-mocked.json` |
| Real E2E manifest | 3/3 passed against the isolated PostgreSQL backend; `reports/agent-workflow/rag-semantic-001-e2e-real-final-2/e2e-real.json` |
| Retrieval campaign | Hybrid hit rate 1.0, MRR 0.90625, source coverage 1.0, p95 782 ms, max query count 2; lexical baseline hit rate/source coverage 0.6875; exactly 17 requests/80 inputs with zero retries and no fallback; summary SHA-256 `5008250c185cc985223b3ed32e3c76aa91114301a0ad0095412bf3b68a68d1fd` |
| Final fast manifest | 13/13 steps passed: 488 backend unit, 23 contract, 182 frontend unit, and production build; `reports/agent-workflow/rag-semantic-001-final-2/fast.json` |
| Independent L3 review | Approved after remediation; no remaining P1/P2/P3 findings |

The ignored retrieval evidence is under
`backend/reports/ai-evaluation/rag-semantic-001/native-pgvector-20260831-3/`.
It binds the approved AI-006 fingerprint, model/provider metadata, exact call
budget, case manifest, report hashes, and activation-gate result without source
content or credentials.

## Post-completion boundary

Keep `RAG_RETRIEVAL_MODE=lexical` until AI-008 thresholds are separately
owner-approved; do not enable AI-008 CI thresholds in this change.

## Rollback

Set `RAG_RETRIEVAL_MODE=lexical` for runtime rollback or `RAG_ENABLED=false` to
disable material chat. The migration downgrade removes only the RAG indexes
and restores the exact pre-migration `vector(1536)` schema without dropping the
shared extension.
