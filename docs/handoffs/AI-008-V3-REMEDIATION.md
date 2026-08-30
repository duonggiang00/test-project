# Handoff: AI-008 v3 Minimal Remediation

Status: BLOCKED

Risk level: L3 governed AI evaluation

## Outcome

- Added versioned `ai-008-v3` evaluation support using Llama 3.3 70B while
  preserving production model behavior and V1/V2 evidence.
- Reused the existing DeepInfra-only JSON workflow, zero retries, ten-case
  canary, deterministic evaluator, and comparison artifacts.
- Added fail-closed 40/80-call authorization bound to the exact ordered ledger,
  prior candidates, reviews, observations, deterministic report, and hard gates.
- Independent pre-call review closed one P1, one P2, and one P3; final pre-call
  verdict had no unresolved P1/P2/P3.
- The live campaign stopped after five calls when `qgen-006` failed the strict
  JSON envelope. No retry or later call was made.
- AI-008 remains blocked and CI thresholds remain disabled.

## Verification

- Focused V3 tests: 44 passed.
- AI-related unit tests: 261 passed.
- Ruff, Mypy, architecture guard, and `git diff --check`: passed.
- Backend gate: 438 unit, 24 contract, and 171 PostgreSQL integration tests;
  `reports/agent-workflow/ai-008-v3-final2-backend/backend.json`.
- Fast gate: 13/13 steps, including 438 backend unit, 24 contract, 182
  frontend tests, and production build;
  `reports/agent-workflow/ai-008-v3-final3-fast/fast.json`.
- Legacy evidence: all 18 V1/V2 files remain byte-identical by SHA-256.
- Final independent L3 review: approved with no unresolved P1/P2/P3.

## Impact

- Product API/database/auth/RAG behavior: unchanged.
- Production `AI_DEFAULT_MODEL`: unchanged.
- Dependencies and migrations: none.
- Ignored V3 evidence: five reservations and five terminal attempts.

## Follow-up

V3 is terminal and must not resume. Any V4 proposal requires separate owner
approval and must preserve V1-V3 evidence.

## Rollback

Revert the scoped V3 commit. No application or database rollback is required.
