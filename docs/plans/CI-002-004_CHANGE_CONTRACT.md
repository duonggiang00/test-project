# Change Contract: CI-002 through CI-004 — Fast, Integration, and Migration Gates

Risk level: L3 for isolated migration execution; L1 for workflow configuration  
Owner: Primary Codex agent  
Approval required: Yes for migration execution  
Approval evidence: The owner approved execution of the canonical optimization plan; each local create/migrate/drop command remains subject to explicit tool approval.

## Scope

- In scope:
  - Replace the legacy install-only workflow with a PR/push fast gate and a push-to-`main` PostgreSQL integration gate.
  - Use verified current major versions of official GitHub/Astral actions and a pinned pgvector PostgreSQL image.
  - Upload JUnit, Jest, and build diagnostics on failure.
  - Add an isolated Alembic upgrade → downgrade → upgrade runner using the guarded `_test` database lifecycle.
- Out of scope:
  - Application migration changes.
  - Mocked or real E2E jobs (`CI-005` and `CI-006`).
  - Browser matrix and visual regression.
  - Remote branch-protection configuration (`CI-010`).

## Behavior

- Before:
  - CI uses Node 18 and legacy action majors, installs backend dependencies, and never runs backend tests.
  - No PostgreSQL service or migration round trip exists.
- After:
  - Pull requests and pushes to `main` run the shared fast gate with a five-minute timeout.
  - Pushes to `main` run the guarded PostgreSQL integration gate with a ten-minute timeout.
  - The migration runner creates a new local `_test` database, runs upgrade/downgrade/upgrade, and drops the target in `finally`.
- Preserved invariants:
  - Local Windows and CI invoke the same logical entry points.
  - No shared, developer, staging, or production database is migrated.
  - Workflow permissions remain read-only.

## Expected files and contracts

- Files/modules:
  - `.github/workflows/ci.yml`
  - Verification/report orchestration and migration lifecycle scripts
  - CI and verification documentation/tracker
- API/event/schema impact: None.
- Migration/data impact: Existing migrations execute only against a newly created isolated `_test` database.
- Security/ownership/tenant impact: None; workflow token permission is `contents: read`.

## Verification contract

- Targeted tests: Existing config and test-database safety unit tests.
- Static/type checks: Parse workflow YAML and check orchestration syntax.
- Integration/PostgreSQL checks: Local guarded integration pass and Alembic round trip.
- Build/E2E/visual checks: Fast gate includes production build; E2E is deferred.
- Manual verification: Inspect triggers, timeouts, action versions, service health check, artifacts, and final database absence.

## Rollback

- Code rollback: Restore the previous workflow and remove the migration mode.
- Data rollback: The isolated runner drops only the target it created; an interrupted run can be inspected and removed with the guarded explicit drop command.

## Assumptions and drift

- Verified assumptions:
  - Fast gate passes locally under five minutes.
  - PostgreSQL integration passes locally under ten minutes and cleans up.
  - The repository currently has no Git remote, so GitHub-hosted verification cannot run yet.
- Unresolved assumptions:
  - GitHub-hosted action execution remains `REVIEW` until the repository is committed and pushed.
- SPEC_DRIFT:
  - The replaced workflow installed backend dependencies but did not execute backend tests.
  - The initial Alembic migration cannot upgrade a fresh database because it drops `ix_user_email` before that index exists. Fixing migration history requires separate owner approval.
