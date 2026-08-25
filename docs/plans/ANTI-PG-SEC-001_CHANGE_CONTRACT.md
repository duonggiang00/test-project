# Change Contract: ANTI-PG-SEC-001 — PostgreSQL Anti-Pattern and Session Security Repair

Risk level: L4 authentication replacement; L2 query and demo-loader refactor
Owner: Primary implementation agent
Independent review: Security reviewer required
Approval required: Yes
Approval evidence: Project owner approved implementation of the proposed plan on 2026-08-25. The existing `SEC-001-007_CHANGE_CONTRACT.md` and `REMAINING_HIGH_RISK_APPROVAL_PACKET.md` remain authoritative for the authentication defaults. The owner also authorized destructive reset of verified local development databases and selected student-only self-service semantics for SEC-006.

## Scope

- In scope:
  - Establish a disposable local PostgreSQL development/test baseline.
  - Remove the ten active backend architecture-guard findings without changing demo-data semantics.
  - Remove password-reset secret output and close duplicate-registration races.
  - Implement SEC-003, SEC-004, SEC-005, and SEC-007 using the approved access/refresh, revocation, CSRF, and redirect contract.
  - Resolve SEC-006 by keeping student self-service routes student-only and preserving separate audited admin management flows.
- Out of scope:
  - MySQL, production password-reset delivery, OAuth, teacher sharing, admin submission impersonation, AI backlog expansion, and unrelated repository cleanup.

## Behavior

- Before:
  - Four legacy `Session.query()` calls and six query-in-loop findings remain.
  - Password-reset secrets are printed to stdout.
  - Access tokens last seven days and have no refresh, rotation, replay, or revocation lifecycle.
  - The BFF stores one access token plus a browser-readable role cookie and has no CSRF contract.
- After:
  - SQLAlchemy 2.x queries are set-based; the only bounded dependency-order delete loop is an explicit measured waiver.
  - Reset secrets cross only an injected delivery boundary and never enter application logs or public responses.
  - Access tokens last 15 minutes; hashed opaque refresh sessions rotate atomically with the approved 7/30-day and five-second replay rules.
  - Current/all-session logout, password-change revocation, inactive-user rejection, CSRF/origin enforcement, credential stripping, server-hydrated roles, and canonical redirects are implemented.
- Preserved invariants:
  - PostgreSQL remains the official database and the BFF remains the only browser-to-backend boundary.
  - Canonical `{error_code, details, request_id}` errors and atomic required audit events remain unchanged.
  - Ownership is backend-enforced; inaccessible cross-owner resources do not leak existence.

## Expected files and contracts

- Files/modules:
  - Backend auth/security/models/migrations, auth service/endpoints, demo-data loader, and PostgreSQL tests.
  - Frontend auth BFF routes, generic proxy, auth hydration/redirect state, and contract/E2E tests.
  - Architecture guard baseline/fixtures and project tracker/handoff.
- API/event/schema impact:
  - Add backend refresh, logout, and logout-all contracts.
  - Login adds a refresh secret to the server-to-server response; browser responses expose neither token.
  - Add required auth revocation/replay/logout audit events without secret fields.
- Migration/data impact:
  - Add non-null active-user state and a hashed refresh-session/token-family table through a downgradeable Alembic revision.
  - Local `test_project_db` and its `_test` derivative are disposable after exact-host/name validation; shared and production databases remain prohibited.
- Security/ownership/tenant impact:
  - Authentication lifecycle and cookie contracts change under the existing owner approval.
  - Student self-service remains student-only. Admin management access remains separate and audited.

## Verification contract

- Targeted tests:
  - Duplicate registration, reset-secret non-disclosure, set-based query budgets, access/refresh expiry, rotation/replay, revocation, inactive actors, and authorization matrices.
- Static/type checks:
  - Ruff, mypy, architecture guard with zero active debt, frontend lint/type checks, and OpenAPI contract review.
- Integration/PostgreSQL checks:
  - Guarded disposable database lifecycle, full integration, concurrency, migration upgrade/downgrade/upgrade, model drift, and cleanup confirmation.
- Build/E2E/visual checks:
  - Next.js build, mocked E2E, and real-backend login-refresh-logout/redirect coverage across required browser projects. No visual changes are planned.
- Manual verification:
  - Inspect Set-Cookie attributes, CSRF failure behavior, sanitized logs, canonical redirects, and final database cleanup.

## Rollback

- Code rollback:
  - Revert application changes, revoke all refresh sessions, and force re-login. Keep additive schema columns when rolling back only application behavior.
- Data rollback:
  - For local development, verify the exact local target, drop it, and recreate it from the selected code revision with `alembic upgrade head`. Never downgrade a shared/live database merely to roll back application code.

## Assumptions and drift

- Verified assumptions:
  - PostgreSQL 18 is accepting connections on local port 5432.
  - The baseline had ten active architecture-guard findings and no refresh-session model; the implemented state has zero active findings and one task-linked teardown waiver.
  - `User.is_active` and the hashed `refresh_sessions` model are present at Alembic head `a74c9d2e6f10`.
  - Guarded PostgreSQL integration, migration round-trip, and real E2E all pass, and the managed `_test` database is absent afterward.
- Unresolved assumptions: none for the approved local verification scope.
- Independent review result:
  - Final PostgreSQL-enabled read-only re-review found no remaining P1/P2 after the initial findings and executable-gate regressions were remediated.
- Resolved SPEC_DRIFT:
  - The permission matrix previously granted Admin student-submission self-service actions while live routes required a Student actor. The owner selected the safer student-only behavior on 2026-08-25; the matrix and regression tests now match that decision.
