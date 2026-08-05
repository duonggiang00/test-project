# Change Contract: TOOL-008 and TOOL-009 — Isolated PostgreSQL and Containerization Path

Risk level: L2  
Owner: Primary Codex agent  
Approval required: Yes for destructive database execution  
Approval evidence: The owner approved execution of the canonical optimization plan; each create/test/drop command remains subject to an explicit tool approval.

## Scope

- In scope:
  - Derive or accept a dedicated PostgreSQL test URL without changing the development URL.
  - Add a guarded local test-database lifecycle that creates a new `_test` database, runs integration tests, and drops only the database it created.
  - Refuse remote hosts, non-test names, the admin database, the development database, and pre-existing target databases.
  - Make shared `backend`, `integration`, and `all` verification modes use the guarded lifecycle.
  - Document a future optional container boundary without making Docker part of daily Windows development.
- Out of scope:
  - Production/shared database operations.
  - Alembic round-trip verification (`CI-004`).
  - Application migrations or model changes.
  - A mandatory Docker or Compose implementation.
  - Deployment topology.

## Behavior

- Before:
  - Integration tests connect to the same URL as the application and may leave test records in a developer database.
  - PostgreSQL provisioning and cleanup are manual.
- After:
  - Unit tests remain database-independent.
  - Integration tests require `ENV=test` and a local database whose name ends in `_test`.
  - The runner creates a previously nonexistent target, runs marked integration tests, and drops that exact target in `finally`.
  - Existing target databases are never reused or dropped automatically.
- Preserved invariants:
  - PostgreSQL remains canonical.
  - The development database URL is unchanged.
  - No application schema, API, auth, ownership, or tenant behavior changes.

## Expected files and contracts

- Files/modules:
  - `.env.test.example`, `.gitignore`
  - Backend settings and settings tests
  - Backend test guard and PostgreSQL lifecycle scripts
  - Shared verification orchestrator and verification docs
  - Optional containerization-path documentation
- API/event/schema impact: None.
- Migration/data impact: Create and drop a guarded local `_test` database only.
- Security/ownership/tenant impact: None in application behavior; test isolation is strengthened.

## Verification contract

- Targeted tests:
  - Settings derivation and explicit test URL tests.
  - Pure safety-policy tests for allowed and rejected database targets.
- Static/type checks:
  - Python collection and Node syntax checks.
- Integration/PostgreSQL checks:
  - Observe create → 24 integration tests → drop.
  - Confirm the target does not exist after the runner exits.
- Build/E2E/visual checks: Not applicable to the database lifecycle; retain the already-green fast gate.
- Manual verification:
  - Inspect sanitized host/database output only; never print credentials.

## Rollback

- Code rollback: Revert the scoped runner/config files and restore the previous verification mapping.
- Data rollback: The runner drops only the database it created; if interrupted, run the guarded `drop` command after confirming the sanitized target name.

## Assumptions and drift

- Verified assumptions:
  - The current base PostgreSQL host is `localhost` and the base database is `test_project_db`.
  - The derived isolated target is `test_project_db_test`.
  - The current database role can run the existing integration suite; create-database permission remains to be executed and verified.
- Unresolved assumptions:
  - The current local PostgreSQL role may not have `CREATEDB`; failure must be reported without weakening safeguards.
- SPEC_DRIFT:
  - Existing integration tests currently use the application database directly, contrary to the canonical isolated-test requirement.
