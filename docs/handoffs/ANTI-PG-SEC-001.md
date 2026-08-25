# Handoff: ANTI-PG-SEC-001 PostgreSQL anti-pattern and session security repair

Status: DONE
Risk level: L4 authentication; L2 query remediation

## Outcome

- Requirements/task IDs: `ANTI-PG-SEC-001`, `SEC-003`, `SEC-004`, `SEC-005`, `SEC-006`, `SEC-007`.
- Removed all ten active backend query anti-pattern findings. The guard now reports zero active debt and one task-linked waiver for the fixed dependency-order teardown loop.
- Added short-lived access tokens and hashed opaque refresh sessions with rotation, family-scoped replay revocation, current/all-session logout, inactive-user rejection, and revocation after password change/reset or account disable.
- Replaced browser-readable auth state with HttpOnly access/refresh cookies, same-origin double-submit CSRF protection, credential-stripping BFF forwarding, one-retry refresh, server-hydrated roles, and canonical redirects.
- Kept student exam self-service routes student-only and amended the permission matrix to distinguish those routes from audited admin management flows.
- PostgreSQL integration, concurrency/query-budget coverage, migration round-trip, and real-backend E2E all passed against a guarded disposable local test database; final status confirms that database was removed.

## Files changed

- `backend/app/services/auth_service.py`, `auth_session_service.py`, and `password_reset_delivery.py` - SQLAlchemy 2.x auth queries, duplicate-registration race handling, secret-safe reset delivery, and session lifecycle.
- `backend/app/models/refresh_session.py`, `models/user.py`, and `alembic/versions/a74c9d2e6f10_add_refresh_sessions.py` - active-user and hashed refresh-session schema.
- `backend/app/api/deps.py`, `api/endpoints/auth.py`, and auth schemas/configuration - access-session validation and refresh/logout contracts.
- `backend/app/demo_data/loader.py` and architecture guard files - set-based reads/counting and a task-linked bounded teardown waiver.
- Frontend auth BFF routes and `frontend/src/lib/server-auth.ts`, `csrf.ts`, `api.ts`, and `store.ts` - cookie, CSRF, refresh, proxy, logout, and cache contracts.
- Frontend protected/auth layouts, headers, and `useCurrentUser.ts` - backend-hydrated role gating and deterministic redirects.
- Backend/frontend unit, contract, integration, component, and mocked E2E tests - regression coverage for the changed boundaries.
- Generated OpenAPI, project inventory, model signature, permission matrix, and architecture baseline - synchronized contracts.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `node scripts/verify.mjs fast` | 0 | 487 tests | 487 | 0 | 679 backend deselections | `VERIFY_OK mode=fast`; 323 backend unit, 18 contract, 63 frontend unit, 83 component, lint/type/contracts/build passed. |
| `node scripts/verify.mjs integration` | 0 | 169 | 169 | 0 | 341 deselected | PostgreSQL integration, concurrent refresh/registration, authorization serialization, and query budgets passed; managed database dropped. |
| `node scripts/verify.mjs migration` | 0 | 5 migration stages plus downgrade guards | All | 0 | 0 | Upgrade to `a74c9d2e6f10`, downgrade to base, upgrade to head, and exact schema assertions passed; managed database dropped. |
| `node scripts/verify.mjs e2e-real` | 0 | 3 | 3 | 0 | 0 | Admin/student login and Student exam start/submit/result passed against FastAPI and PostgreSQL; owner/flake policy passed. |
| `node scripts/verify.mjs e2e-mocked` | 0 | 28 | 28 | 0 | 0 | Chromium, Firefox, WebKit, and mobile Chrome passed; `PLAYWRIGHT_POLICY_OK tests=28`. |
| `node scripts/architecture-guard.mjs fixtures` | 0 | 23 bad fixtures / 21 rules | All | 0 | 0 | `ARCHITECTURE_FIXTURES_OK good=0 bad=23 rules=21`. |
| `node scripts/architecture-guard.mjs check` | 0 | 0 active / 1 waiver | All | 0 | 0 | `ARCHITECTURE_OK current=0 baseline=0 waivers=1`. |
| Independent security re-review | 0 | Latest uncommitted diff | No P1/P2 | 0 | 0 | Reviewer confirmed logout/role hydration, `FOR SHARE OF users`, refresh self-FK ordering, public-Host origin validation, migration oracle, and PostgreSQL evidence. |
| `uv run --frozen python -m scripts.test_database status` | 0 | 1 target | 1 | 0 | 0 | Final state: `test_project_db_test` is absent on `localhost:5432`. |
| `git diff --check` | 0 | Changed diff | All | 0 | 0 | No whitespace errors; one existing CRLF normalization warning only. |

## Impact

- API/event/schema contract: login response gains refresh/expiry fields; `/auth/refresh`, `/auth/logout`, and `/auth/logout-all` are added; revocation/replay audit actions are registered.
- Migration/data: additive `users.is_active` plus `refresh_sessions`; guarded upgrade/downgrade/upgrade and exact head/base schema checks passed.
- Security/ownership/tenant: authentication lifecycle changes under prior owner approval; access tokens are 15 minutes and refresh lifetimes are 7/30 days; student self-service stays student-only.
- Dependency/toolchain: no dependency was added. PostgreSQL remains mandatory; no SQLite or MySQL compatibility path was introduced.

## Manual evidence

- Scenario: inspect generated OpenAPI, model signature, architecture waiver, Set-Cookie/CSRF assertions, sanitized logs, and the initial real-E2E origin-failure artifact.
- Result: generated contracts match the code; the artifact identified the internal-URL/public-Host mismatch, the exact-origin fix passed unit and real E2E, and automated checks prove HttpOnly token cookies, credential stripping, canonical failures, and no reset-token stdout leak.
- Screenshot/trace: the initial failed real-E2E desktop screenshots were inspected; the corrected run passed 3/3. Existing mocked visual regressions passed across four projects. No visual baseline changed.

## Risks and follow-up

- Known risks: the real E2E logs an existing pagination-extension recommendation and an expected retained-record delete conflict during cleanup; neither failed the flow, and the isolated database was dropped.
- Unverified items: no required local gate remains. GitHub-hosted CI execution is outside this local implementation scope.
- Follow-up tasks: create a scoped commit/PR when requested; keep PostgreSQL credentials only in the ignored local `.env`.

## Rollback

- Code: revert the `ANTI-PG-SEC-001` change set, revoke all issued refresh sessions, and force re-login.
- Data: after validating the exact local development target, drop/recreate it and run `alembic upgrade head` at the selected revision. Never apply destructive rollback to a shared environment.
