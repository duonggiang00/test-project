# Handoff: AI-008 v4 Deterministic Envelope Recovery

Status: BLOCKED

Risk level: L3 governed AI evaluation

## Outcome

- Added the separately versioned `ai-008-v4` campaign without changing the
  production AI adapter, API, database, authentication, RAG, or CI thresholds.
- V4 keeps the approved Llama 3.3 70B model, DeepInfra-only routing, JSON mode,
  temperature zero, 1000-token cap, zero retries, and the 120-call ledger.
- V4 applies the existing production JSON extractor followed by the unchanged
  strict `CandidateEnvelope` validator. Multiple fenced or mixed JSON payloads
  fail closed; raw provider text is retained only in ignored evidence with its
  SHA-256 hash.
- Independent pre-call L3 review approved the implementation with no
  remaining P1/P2/P3 findings.
- Live execution stopped permanently after the approved ten-call canary:
  format 10/10, citations 10/10, injection resistance 8/8, safe continuation
  5/8, required refusal 0/1. No 40-call gate or later call was authorized.
- AI-008 remains blocked and no CI threshold was proposed or enabled.

## Verification

- Focused V4/legacy evaluation tests: 48 passed.
- AI-related unit tests before live execution: 228 passed.
- Ruff, Mypy, architecture guard, and `git diff --check`: passed.
- Backend gate: 442 unit, 24 contract, and 171 PostgreSQL integration tests;
  `reports/agent-workflow/ai-008-v4-final/backend.json`.
- Fast gate: 13/13 steps, including 442 backend unit, 24 contract, 182
  frontend tests, and production build;
  `reports/agent-workflow/ai-008-v4-final/fast.json`.
- Canary evidence: `backend/reports/ai-evaluation/ai-008-v4/` (ignored).

## Impact and follow-up

- V1-V3 run/campaign/comparison serialization remains compatible; V4-only parse
  metadata is omitted from legacy files.
- The V4 campaign is terminal and must not resume. A new campaign requires a
  separately approved remediation addressing safe continuation and explicit
  refusal quality, with a new prompt/model policy or an owner-approved scope.

## Rollback

Revert the scoped V4 commit. No application or database rollback is required.
