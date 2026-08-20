# Handoff: BASE-001 standardize the grade-correction feature

Status: DONE
Risk level: L3

## Outcome

- Summary: GRADE-001 (a teacher or admin correcting one submission
  answer's score, with a mandatory reason, an atomic audit event, and a
  recomputed submission total) is now packaged and hardened as an
  official product feature: exact migration schema assertions for its
  three grade-override-trail columns, an English/strict-black-and-white
  History UI, a mocked E2E suite running against a real production build
  with self-healing server-port cleanup, and a completed independent
  re-review. No API, permission, or audit-schema change — GRADE-001's
  design is unchanged, only packaged and hardened.
- Requirements/task IDs: BASE-001 (all six subtasks DONE — see
  `BASE-001_TASK_TRACKER.md`).

## Files changed

- `backend/scripts/run_migration_roundtrip.py` — exact column/FK
  (`ON DELETE SET NULL`)/index assertions for the three grade-override
  columns, reported as `grade_override_columns=3
  grade_override_foreign_keys=1 grade_override_indexes=1` at head and
  `0/0/0` at base and every prior revision (commit `3fcc57e`).
- `frontend/src/app/(admin)/history/[id]/page.tsx`,
  `AnswerGradeEditor.tsx` — translated to English, gray Tailwind classes
  replaced with black/white; validation, disabled states, and error
  mapping unchanged (commit `37777b2`).
- `frontend/tests/component/submission-grade-override.test.tsx`,
  `frontend/tests/e2e/grade-submission-flow.spec.ts` — updated to assert
  the English copy.
- `frontend/playwright.mocked.config.ts`, new
  `scripts/build-e2e-mocked.mjs`, `scripts/verify.mjs` — mocked E2E now
  runs `next build --webpack` (`NEXT_DIST_DIR=.next-e2e-mocked`) once as
  a `verify.mjs` pre-step, then `next start` (not `next dev`) as
  Playwright's `webServer`, with an explicit 120s startup timeout and
  `stdout`/`stderr: 'pipe'` so the server's own console output is
  captured, not silently dropped (commit `c5e8b4b`); the build script
  also frees any stale listener already on the target port before
  building, so a prior crashed/timed-out run self-heals instead of
  hard-failing the next one with a misleading "port already used"
  (commit `7200a90`).
- `config/architecture-guard-baseline.json` — regenerated to drop five
  dead fingerprints left by the deleted Vietnamese/gray lines (same
  commit).
- `docs/plans/BASE-001_CHANGE_CONTRACT.md`, `BASE-001_TASK_TRACKER.md`,
  this handoff.

## Verification

| Command | Result |
|---|---|
| `node scripts/verify.mjs fast` | `VERIFY_OK` at every commit; final run: 302 backend unit, 15 contract, 49 frontend unit, 62 frontend component, production build clean, architecture guard `150/150` |
| Guarded PostgreSQL integration (full) | 156 passed, 0 failed |
| Guarded migration round trip | Clean through head `b6d4f0a17c53`; grade-override exact-schema counts (3 columns/1 FK/1 index) confirmed at every checkpoint |
| `node scripts/verify.mjs e2e-mocked` | 5 consecutive solo runs, **28/28 passed every time** (140/140 individual test executions) against the production-build server |
| Independent review | See below |

## Independent review and remediation

A reviewer agent read the translation commit against its pre-commit
Vietnamese originals (via `git show 37777b2^:...`), confirmed no logic was
hidden inside the language/color pass, confirmed the architecture guard's
gray-token rule is real (live-tested by reintroducing a gray class and
watching it fire), confirmed the E2E build/start wiring reads and writes
the same `NEXT_DIST_DIR`, and confirmed the failure-artifact capture claim
by deliberately breaking an assertion and finding the resulting
screenshot/video/error-context on disk. No P1 findings.

Two P2s, both closed before sign-off (commit `7200a90`):

1. **Mocked-E2E flakiness contradicted the "stabilize" framing.** The
   reviewer's own run hit a webkit timeout in the unrelated
   `admin-flow.spec.ts`. Investigated: five further solo runs (no
   concurrent build/test load sharing the machine, unlike the review
   run, which overlapped with other heavy processes) passed 28/28 every
   time. Documented as resource-contention-induced flakiness during a
   concurrent review, not a regression from switching `next dev` →
   `next start`, rather than papering over it with an unevidenced
   timeout bump.
2. **An orphaned `next start` process could hold the port after a
   crashed/timed-out run**, making the *next* invocation hard-fail with a
   misleading "port already used" error instead of surfacing whatever
   actually failed. Fixed: `build-e2e-mocked.mjs` now frees any stale
   listener on the target port (via `netstat`/`taskkill` on Windows,
   `lsof`/`kill` elsewhere) before every build, best-effort and silent on
   a missing platform tool. Verified directly by starting a dummy
   listener and confirming the script killed it before building.

Two P3s: dead architecture-guard baseline fingerprints (cleaned in the
same commit); a generated `project-inventory.json` diff whose provenance
pointed at a concurrently-landing, unrelated commit (harmless, noted for
awareness). One P3 (Vietnamese text in a component test's *mock fixture
data*, representing a teacher's free-text input, not app UI copy) was
correctly left alone — out of scope for a UI translation pass.

## Impact

- API/event/schema contract: none.
- Migration/data: none (BASE-001 added test coverage for GRADE-001's
  existing migration, not a new one).
- Security/ownership/tenant: none.
- Dependency/toolchain: none. `next build --webpack` / `next start`
  already existed in this project's toolchain (used by the regular
  production-build fast gate); this reuses it for the mocked E2E server
  instead of introducing anything new.

## Known risks and follow-up

- The five-run flake investigation is reassuring but not exhaustive —
  if webkit-specific timing issues resurface under real CI load
  (out of scope for this contract, since GitHub Actions configuration
  was explicitly excluded), the failure will at least no longer be
  masked by a stale-port false failure on the next attempt.
- No new permanent tool was built for the earlier DATA-DEMO-002 local
  database reset; see that handoff's own follow-up note.

## Rollback

- Code: revert the relevant commit(s). No migration or schema change to
  roll back.
- No data impact.
