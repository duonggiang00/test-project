# Change Contract: RAG-SEMANTIC-001 Hybrid Retrieval

Risk level: L3 sensitive retrieval, migration, and breaking legacy API removal

Owner approval: `REMAINING_WORK_EXECUTION_PLAN_2026-08-25.md` explicitly
approves pgvector installation, PostgreSQL 18/pgvector 0.8.6 alignment,
semantic hybrid retrieval, lexical rollback, and removal of
`POST /ai/process-document`.

Independent review: Required before activation and completion.

## Goal

Replace mock embeddings and keyword/last-chunk retrieval with evaluated,
owner-scoped pgvector plus PostgreSQL full-text retrieval while retaining an
immediate lexical rollback mode.

## Scope

- Add a typed embedding provider boundary and an OpenRouter implementation.
- Default the embedding policy to `openai/text-embedding-3-small` with exactly
  1536 dimensions; keep the model configurable and validate dimensions.
- Generate real embeddings in one bounded batch when uploaded material is
  chunked; never issue provider or database calls inside a chunk loop.
- Remove the PostgreSQL `Vector -> VARCHAR` compiler override.
- Add a downgradeable migration that requires pgvector, converts the legacy
  text-compatible embedding column to `vector(1536)`, and adds HNSW cosine and
  PostgreSQL full-text indexes.
- Add owner-material-scoped vector and lexical ranking with reciprocal-rank
  fusion and deterministic tie breaking.
- Add `RAG_RETRIEVAL_MODE=lexical|hybrid`; `lexical` remains the default until
  the owner approves AI-008 thresholds and the retrieval evaluation passes.
- Emit sanitized source identifiers and retrieval mode in chat source/audit
  events without exposing another owner's chunks or raw restricted payloads.
- Remove the explicitly approved compatibility-only
  `POST /ai/process-document` route, schema, service path, and tests.
- Align GitHub PostgreSQL services to PostgreSQL 18 with pgvector 0.8.6.
- Run the isolated Alembic round trip in the pull-request PostgreSQL job so
  pgvector upgrade/downgrade evidence is available before merge.
- Add a deterministic lexical-versus-hybrid retrieval evaluator using the
  approved RAG cases plus same-material distractors.
- Bind each canonical dataset source label to a material-scoped chunk UUID in
  the evaluation manifest; do not score opaque UUIDs as dataset labels.
- Require the approved AI-006 fingerprint and fixed 1.0 hit-rate/source-coverage
  floors before a retrieval report can pass.

## Out of scope

- AI-008 threshold approval or CI activation.
- Changing the production chat completion model or prompt.
- Cross-material or cross-owner retrieval.
- Automatic publishing, grading, fallback completion models, reranking
  providers, document OCR, or chunking redesign.
- Persisting raw provider requests/responses or unrestricted document text in
  audit events.

## Constraints

- The backend kill switch remains authoritative and fails before auth,
  retrieval, or provider work.
- Authorization resolves one owned/admin-overridden material before either
  ranking branch executes; material scoping is repeated inside both SQL
  ranking branches.
- Provider errors remain sanitized. Operator rollback is the explicit lexical
  mode; hybrid mode must not silently claim semantic retrieval after an
  embedding failure.
- Embedding vectors must be finite, exactly 1536 values, and bound to the
  configured model/dimension policy.
- Migration extension creation fails closed. It must not swallow missing
  pgvector or leave a partially converted column.
- Existing data may be dropped/recreated in the approved development
  environment, but upgrade/downgrade behavior remains verified on isolated
  PostgreSQL.
- Semantic mode cannot become the default in code or environment templates
  until the separate owner threshold approval is recorded.

## Acceptance

- Real material chunks and queries use the typed embedding provider; mock
  vectors are absent from executable ingestion paths.
- Hybrid top-k combines cosine and full-text ranks with reciprocal-rank fusion,
  deterministic ordering, and no query-per-chunk behavior.
- Anonymous, student, inactive, non-owner, owner, and admin cases preserve the
  current tenant-safe behavior and provider non-invocation guarantees.
- Empty material, empty query, invalid dimensions, unavailable provider,
  missing pgvector, tampered mode, and rollback mode have explicit tests.
- The retrieval evaluation records hit rate, MRR, source coverage, latency,
  and query count for lexical and hybrid modes without raw content.
- Hybrid retrieval meets the separately approved safety/quality thresholds
  before any default activation.
- The legacy route is absent from OpenAPI and all frontend/backend call sites.
- PostgreSQL 18/pgvector 0.8.6 migration roundtrip, focused tests, Ruff, mypy,
  architecture, backend, fast, coverage, mocked E2E, real E2E, inventory, and
  `git diff --check` pass.
- Independent L3 review has no unresolved P1/P2/P3 findings.

## Rollback

- Set `RAG_RETRIEVAL_MODE=lexical` for immediate runtime rollback.
- Set `RAG_ENABLED=false` to disable material chat entirely.
- Downgrade the migration on an isolated database to remove the new indexes
  and restore the exact predecessor `vector(1536)` schema; do not remove the
  shared pgvector extension automatically.
- Revert the scoped commits to restore the legacy compatibility route only if
  the breaking-contract rollback is explicitly chosen.

## Current environment evidence

- Local PostgreSQL: 18.6.
- Local pgvector: 0.8.6 is available to PostgreSQL 18 through a verified
  Windows binary distribution and process-scoped PostgreSQL extension/library
  paths; WSL, Docker, service restart, and `Program Files` modification are not
  required.
- The isolated upgrade/downgrade/upgrade migration round trip passes and
  preserves the predecessor material index exactly.
- The complete PostgreSQL integration suite passes 170/170 and drops its
  managed `_test` database after execution.
- CI uses the approved `pgvector/pgvector:0.8.6-pg18` image and runs the
  migration round trip in the pull-request PostgreSQL job.
- The guarded retrieval campaign passed on the approved dataset fingerprint:
  hybrid hit rate and source coverage are 1.0, MRR is 0.90625, and every case
  remains within the two-query budget. The run used exactly 17 requests and 80
  inputs through an OpenAI-only OpenRouter route with zero retries, no fallback,
  required parameter support, and data collection denied. Lexical remains the
  default rollback mode pending the separate AI-008 threshold decision.
- Final verification passes 13/13 fast steps, and independent L3 review reports
  no remaining P1/P2/P3 findings after the zero-retry and activation-eligibility
  remediations.
- The credential-free CI path is covered explicitly: campaign CLI success tests
  inject a test-only placeholder, missing-credential tests remain fail-closed,
  and the complete fast gate passes with `OPENROUTER_API_KEY` empty.
- GitHub Linux visual diagnostics were manually reviewed across desktop/mobile
  Chromium, Firefox, and WebKit before refreshing the affected rasterization and
  intentional AI-review focus/toast baselines; the local four-browser matrix
  then passed 28/28.
