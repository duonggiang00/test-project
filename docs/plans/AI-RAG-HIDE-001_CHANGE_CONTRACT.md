# Change Contract: AI-RAG-HIDE-001 — Temporarily disable RAG

Superseded on 2026-08-25 by the owner-approved `AI-RAG-ENABLE-001` decision. This document is retained as historical implementation evidence.

Risk level: L3 — governed sensitive retrieval behavior  
Owner: Codex  
Approval required: Yes  
Approval evidence: The project owner approved the complete implementation plan in this thread on 2026-08-20.

## Scope

- In scope:
  - Disable material chat and the legacy mock RAG processing endpoint by default.
  - Hide chat controls while preserving upload, extraction, chunking, AI content generation, review, approval, and publication.
  - Record the temporary product-state decision in the canonical specification and optimization tracker.
  - Remove RAG/chat claims from the in-place PlayStudy Google Docs report.
- Out of scope:
  - Deleting RAG implementation, document chunks, embeddings, provider code, or historical engineering evidence.
  - Database migrations, data cleanup, authentication, ownership, CI/CD, AI grading, or generation-pipeline redesign.
  - Local Markdown/DOCX report sources and PDF/DOCX export.

## Behavior

- Before:
  - `POST /ai/chat` and `POST /ai/process-document` are callable whenever the actor passes their normal dependencies.
  - AI Workspace renders material chat together with generation actions.
  - Product specifications and the external report describe RAG as active or under active completion.
- After:
  - `RAG_ENABLED=false` is the backend default and both RAG endpoints return a canonical 404 `FEATURE_NOT_AVAILABLE` before authentication, database retrieval, or provider access.
  - `NEXT_PUBLIC_RAG_ENABLED=false` is the frontend default and AI Workspace renders generation activity without chat input or chat-only guidance.
  - Upload, extraction, chunks, Questions, Flashcards, Topic Briefs, generation review, and publication remain available.
  - The canonical specification marks RAG/chat as temporarily disabled. The external report contains no RAG/chat claims.
- Preserved invariants:
  - Backend ownership remains authoritative for every enabled material and generation operation.
  - AI content still requires review before publication.
  - No persisted data, schema, route payload, cookie, or permission changes.

## Expected files and contracts

- Files/modules:
  - Backend settings and AI Studio endpoint guard.
  - AI Workspace feature presentation and focused backend/frontend tests.
  - Environment example, canonical specification, optimization tracker, and this handoff.
  - Google Doc `16_zCStwiQTuMBRmvs8ILsV3CG6RhqZJivYOd4yDgPRo`, tab `t.0`.
- API/event/schema impact:
  - Existing RAG endpoint shapes remain defined but are runtime-disabled by default with a new stable `FEATURE_NOT_AVAILABLE` error code.
  - No event or schema change.
- Migration/data impact: None.
- Security/ownership/tenant impact:
  - Disabled RAG requests cannot reach authentication, retrieval, audit, or provider boundaries.
  - Enabled generation paths retain their existing authorization.

## Verification contract

- Targeted tests:
  - Backend default-off guard, canonical envelope, and enabled regression behavior.
  - Frontend default-off chat absence/non-call and preserved generation actions.
- Static/type checks: Scoped Ruff/mypy, frontend ESLint, and TypeScript production build.
- Integration/PostgreSQL checks: Focused AI endpoint/ownership integration tests when the guarded test database is available; no migration round trip is required.
- Build/E2E/visual checks: Existing AI review E2E and desktop/mobile AI Workspace evidence when the local browser harness is available.
- Manual verification:
  - RAG controls are absent, RAG endpoints are blocked, and generation remains reachable.
  - Google Docs readback contains zero forbidden RAG/chat phrases in the intended tab.

## Rollback

- Code rollback: Set both feature flags to `true` to restore the retained implementation; revert presentation/spec/report edits if RAG returns to product scope.
- Data rollback: None. No data is changed or deleted.

## Assumptions and drift

- Verified assumptions:
  - `/ai/chat` and `/ai/process-document` are the only current RAG-specific public endpoints.
  - Material generation uses separate `/materials/{id}/generate-*` endpoints.
  - The target Google Doc has one tab (`t.0`).
- Unresolved assumptions: None.
- SPEC_DRIFT:
  - The approved canonical specification currently lists RAG/chat as active MVP scope; this task records the owner's temporary-disable decision without rewriting historical handoffs.
