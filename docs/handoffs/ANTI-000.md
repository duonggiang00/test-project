# Handoff: ANTI-000 Stabilize the remediation baseline

Status: REVIEW
Risk level: L2

## Outcome

- Summary: Existing workspace changes were mapped to their task contracts, the fast no-database gate was repaired for deterministic Windows execution, and the review-stage baseline is ready to checkpoint. PostgreSQL and browser-runtime evidence remain unavailable.
- Requirements/task IDs: `ANTI-000`, `AI-RAG-HIDE-001`, `EXAM-FLOW-QUICK-001`, `STUDENT-EXAM-QUESTION-001`, `STUDENT-UI-QUICK-001`, `STUDENT-UI-QUICK-002`, `WORKSPACE-ARCHIVE-001`.

## Files changed

- Existing task files — retained under their original contracts and handoffs.
- `backend/app/services/grading_service.py` — add the missing typed metadata narrowing required by the configured mypy gate.
- `scripts/verify.mjs` — disable pytest's shared cache provider in fast unit/contract steps to avoid the verified Windows cache ACL failure.
- `docs/plans/ANTI-000_CHANGE_CONTRACT.md` — stabilization contract.
- `docs/generated/project-inventory.json` — regenerated through the canonical generator.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `node scripts/verify.mjs fast` | 0 | Backend 336; frontend 132 | 468 | 0 | Backend 660 deselected | `VERIFY_OK mode=fast`; lint, mypy, generated contracts, architecture guard, Jest, and Next.js build passed. |
| Focused structured-question unit tests | 0 | 16 | 16 | 0 | 0 | Grading and question-draft behavior passed after the typing correction. |
| PostgreSQL affected integration suite | 1 | 0 | 0 | 0 | 0 | Blocked before collection: connection refused at `localhost:5432`; no PostgreSQL server is installed. |
| `node scripts/verify.mjs e2e-mocked` | 1 | 28 planned | 0 | 7 attempted before stop | 21 not run | Playwright browser binaries were missing; the subsequent download was interrupted. |

## Impact

- API/event/schema contract: no new impact from ANTI-000.
- Migration/data: no migration or data mutation.
- Security/ownership/tenant: existing database-sensitive task status remains `REVIEW`; no claim of PostgreSQL verification.
- Dependency/toolchain: pytest cache writing is disabled only for canonical fast unit/contract steps.

## Manual evidence

- Scenario: inspected current task contracts, handoffs, status entries, generated contracts, and the full fast gate output.
- Result: changes are attributable and no fast-gate failure remains; required external runtimes are explicitly blocked.
- Screenshot/trace: existing visual snapshots are retained; no new visual approval was claimed.

## Risks and follow-up

- Known risks: PostgreSQL-sensitive behavior and real-backend E2E remain unverified on this machine.
- Unverified items: integration, migration roundtrip, real E2E, and the complete mocked multi-browser suite.
- Follow-up tasks: continue only with the approved no-database remediation contract; run deferred gates when PostgreSQL and Playwright browsers are available.

## Rollback

- Code: revert the stabilization checkpoint without resetting later work.
- Data: none.
