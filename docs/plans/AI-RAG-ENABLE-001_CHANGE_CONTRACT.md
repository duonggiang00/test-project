# Change Contract: AI-RAG-ENABLE-001 — Re-enable material RAG chat

Risk level: L3 — governed sensitive retrieval behavior
Owner: Codex
Approval required: Yes
Approval evidence: The project owner explicitly directed that RAG/AI be enabled instead of hidden in this thread on 2026-08-25.

## Scope

- In scope:
  - Restore material RAG chat to the active MVP surface by default.
  - Keep the unused compatibility-only mock processing route disabled by default while preserving its explicit regression path.
  - Keep the backend and frontend feature flags as an emergency kill switch.
  - Preserve backend authentication, owner-scoped material retrieval, audit metadata, prompt-injection handling, sanitized provider failures, and BFF-only browser transport.
  - Reject provider-priority client roles and unknown chat-request fields before retrieval or provider access.
  - Repair the retained chat metadata type contract discovered during the re-enable survey.
  - Update the canonical specification, environment example, focused tests, optimization tracker, and engineering handoff.
- Out of scope:
  - Database migrations, data deletion, authentication/session changes, ownership-policy changes, provider replacement, automatic fallback, AI grading, or AI evaluation thresholds.
  - Inventing or approving golden-dataset content.
  - Rewriting the historical `AI-RAG-HIDE-001` contract or handoff.
  - Updating external Google Docs or generated DOCX/PDF reports.

## Behavior

- Before:
  - `RAG_ENABLED` and `NEXT_PUBLIC_RAG_ENABLED` default to `false`.
  - `POST /ai/chat` and `POST /ai/process-document` return `404 FEATURE_NOT_AVAILABLE` unless the backend flag is explicitly enabled.
  - AI Workspace hides material chat unless the frontend flag is explicitly enabled.
- After:
  - `RAG_ENABLED` and `NEXT_PUBLIC_RAG_ENABLED` default to `true`, so authenticated teachers/admins can use owner-scoped material chat without deployment-specific opt-in.
  - `RAG_LEGACY_PROCESS_ENABLED` defaults to `false`; `/ai/process-document` remains a compatibility-only mock route with no frontend call site and requires explicit operator opt-in.
  - Setting `RAG_ENABLED=false` remains the authoritative backend kill switch and returns the same canonical `404 FEATURE_NOT_AVAILABLE` response before authentication, retrieval, or provider access.
  - Setting `NEXT_PUBLIC_RAG_ENABLED=false` hides chat presentation but cannot enable backend access when the backend kill switch is off.
  - Real provider calls still require a configured `OPENROUTER_API_KEY`; failures remain sanitized and are surfaced immediately without raw provider output.
- Preserved invariants:
  - Non-owner and missing material probes are indistinguishable and never invoke the provider.
  - Retrieval context is limited to chunks belonging to the authorized material.
  - AI audit metadata records prompt version, provider/model, and safe context-source identifiers without raw document content.
  - Generated Questions, Flashcards, and Topic Briefs still require review before publication.
  - Browser requests continue through `/api/proxy`; no token or provider key reaches browser state.

## Expected files and contracts

- Files/modules:
  - Environment defaults, backend settings/AI chat metadata, AI Workspace presentation, focused backend/frontend tests, canonical specification, optimization tracker, and handoff.
- API/event/schema impact:
  - No route, response, or audit-event schema changes. The existing chat request is narrowed to the documented `user`/`assistant` roles with unknown fields forbidden; invalid input receives the canonical validation response. Material chat changes from default-disabled to default-enabled runtime behavior; the legacy mock processor remains default-disabled.
- Migration/data impact: None. Existing materials, document chunks, embeddings, audit events, and generation jobs are retained.
- Security/ownership/tenant impact:
  - The existing named owner policy and retrieval scoping become reachable by default for chat; their behavior is not relaxed.
  - Independent L3 security/behavior review remains required before `DONE`.

## Verification contract

- Targeted tests:
  - Default-enabled backend/frontend chat behavior and default-disabled legacy mock processing.
  - Explicit backend/frontend kill-switch behavior.
  - Authentication requirement, sanitized provider failure, selected-material requirement, and no unintended chat call when disabled.
  - Hostile `developer`/`tool` roles and unknown fields fail with `422` before service/provider work.
- Static/type checks:
  - Ruff, expanded AI-module mypy, frontend ESLint, architecture guard, inventory check, and `git diff --check`.
- Integration/PostgreSQL checks:
  - Enabled RAG endpoint behavior, owner-only retrieval, cross-owner/missing indistinguishability, provider non-invocation, and audit persistence using the guarded disposable PostgreSQL runner.
  - Student and inactive denial, owner chat audit metadata, and foreign-owner admin access with both `admin.override` and `ai.chat.requested` evidence.
- Build/E2E/visual checks:
  - Production frontend build and the affected AI review/chat mocked browser flow when available.
- Manual verification:
  - Confirm the configured local environment exposes material chat, an owner can ask about an owned material, and a disabled backend flag still fails closed.

## Rollback

- Code rollback: Set `RAG_ENABLED=false` and `NEXT_PUBLIC_RAG_ENABLED=false`, or revert the scoped enable commit, to restore the previous hidden-by-default state.
- Data rollback: None. No schema or persisted data changes are made.

## Assumptions and drift

- Verified assumptions:
  - `/ai/chat` and `/ai/process-document` remain the only public RAG-specific routes; only chat has a frontend call site and the process route creates synthetic compatibility chunks.
  - AI Workspace calls chat through `/api/proxy/ai/chat`.
  - The local backend environment contains a non-empty provider key without exposing it in repository output.
  - Focused enabled-path PostgreSQL tests pass and drop their managed test database.
- Unresolved assumptions:
  - No live provider request is made during automated verification, so provider-account quota and external availability remain unverified.
- Independent review findings:
  - The first L3 review found no P1 issues and returned two P2 gaps: untrusted client roles could pass through the loose message shape, and the PostgreSQL actor/audit matrix lacked student, inactive, owner-persistence, and admin-override evidence. This contract now includes both remediations and requires reviewer re-verification before `DONE`.
- SPEC_DRIFT:
  - Canonical Section 9.5 still records the previous temporary suspension. This approved task supersedes that product-state decision while retaining the flags as an emergency kill switch.
