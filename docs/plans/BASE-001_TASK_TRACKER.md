# BASE-001 Task Tracker — Standardize the Grade-Correction Feature

Status: In progress
Owner: Primary implementation agent
Parent: `BASE-001_CHANGE_CONTRACT.md`
Created: 2026-08-20

Status values match `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` §2:
`TODO`, `IN_PROGRESS`, `BLOCKED`, `REVIEW`, `DONE`, `DEFERRED`.

## Tasks

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| BASE-001.1 | Exact migration schema assertions for the three grade-override columns (type, nullability, FK `ON DELETE SET NULL`, index) | DONE | GRADE-001 | `MIGRATION_SCHEMA_ASSERTIONS_PASSED` reports `grade_override_columns=3 grade_override_foreign_keys=1 grade_override_indexes=1` at head and `0/0/0` at base and every prior revision, at every stage of the guarded round trip (commit `3fcc57e`) |
| BASE-001.2 | Change contract, task tracker, handoff (English) | IN_PROGRESS | — | This tracker and `BASE-001_CHANGE_CONTRACT.md` exist; `docs/handoffs/BASE-001.md` written once BASE-001.5 lands |
| BASE-001.3 | History UI: English text, strict black-and-white, intact keyboard/focus/error states | DONE | — | Commit `37777b2`. Architecture guard `current=150 baseline=161`, zero gray/named-color violations |
| BASE-001.4 | Mocked E2E on a dedicated production build (`NEXT_DIST_DIR=.next-e2e-mocked`, `next build --webpack`, `next start`), explicit startup timeout, guaranteed failure artifacts | DONE | — | Commit `c5e8b4b`. `node scripts/verify.mjs e2e-mocked` 28/28 across 4 browsers; deliberate-failure artifact capture proven |
| BASE-001.5 | Independent review: re-verify ownership, 404-indistinguishability, bounds, total-recomputation, audit-atomicity, and concurrency invariants, plus translation/behavior-parity/E2E-wiring review | IN_PROGRESS | BASE-001.1, 3, 4 | Reviewer report with no P1 findings, or all P1/P2 findings closed before sign-off |
| BASE-001.6 | Final verification and handoff | TODO | BASE-001.1–5 | `docs/handoffs/BASE-001.md` records fast/integration/migration-roundtrip/e2e-mocked results |

## Progress log

| Date | Task | Status | Notes |
|---|---|---|---|
| 2026-08-19 | GRADE-001 (all) | Completed | Backend (`f01c85b`), frontend (`2afc2c8`, `16d946e`, `c1a8ed1`), migration downgrade-guard test coverage (`e087844`) — see `docs/handoffs/GRADE-001.md` if present, or the BASE-001 handoff, for full detail. Independent review found no P1s. |
| 2026-08-20 | BASE-001.1 | Completed | Exact grade-override schema assertions added to the migration round-trip runner (commit `3fcc57e`). |
| 2026-08-20 | BASE-001.2 | In progress | Change contract and this tracker written. |
