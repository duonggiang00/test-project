# Handoff: DATA-001 audit core and DATA-006 retention decision

Status: DONE
Risk level: L4 — additive migration, security/privacy, and API error contract

## Outcome

- Summary: Added the canonical append-only audit-event foundation, strict
  action-specific privacy validation, request correlation, canonical structured
  API errors, safe frontend localization, and the approved MVP retention
  decision. No required business action is instrumented yet; that remains
  DATA-002.
- Requirements/task IDs: DATA-001, DATA-006.

## Files changed

- `backend/alembic/versions/b57c9a14d2e8_add_audit_events.py` — additive audit
  schema, constraints, indexes, and append-only PostgreSQL triggers.
- `backend/app/models/audit_event.py`, `backend/app/schemas/audit.py`,
  `backend/app/services/audit_service.py`, and
  `backend/app/services/audit_policy.py` — model, typed event contract,
  transaction-neutral writer, and deny-by-default action policies.
- `backend/app/core/correlation.py`, `backend/app/core/error_handlers.py`,
  `backend/app/core/safe_payload.py`, and `backend/app/core/exceptions.py` —
  correlation, canonical errors, protocol-header preservation, and structured
  payload privacy validation.
- `backend/app/main.py`, `backend/app/api/deps.py`,
  `backend/app/api/endpoints/materials.py`, and
  `backend/app/services/auth_service.py` — middleware/handler registration and
  production-route adoption of the canonical contract.
- `backend/scripts/run_migration_roundtrip.py`, backend audit/error/migration
  tests, `backend/pyproject.toml`, and model/inventory signatures — exact schema,
  immutability, redaction, correlation, lint/type, and generated-drift evidence.
- `frontend/src/lib/errors.ts`, `frontend/src/lib/server-errors.ts`, BFF routes,
  `frontend/src/services/apiService.ts`, and affected UI consumers — stable
  English localization, correlated canonical BFF failures, safe logging, and
  service-owned AI transport.
- Frontend route/service/component tests — error canaries, protocol headers,
  generated correlation, material cascade context, AI stream/save/upload
  failures, and auth/profile/exam error states.
- `frontend/tests/pom/StudentExamPage.ts` — narrowed the real-E2E selector from
  a broad border container to the exact exam row and `LÀM BÀI` button after a
  strict-mode failure proved the old selector matched six buttons.
- `docs/spec/CANONICAL_PROJECT_SPEC.md`, the approved change/approval contracts,
  this tracker/handoff, and `docs/generated/project-inventory.json` — durable
  decision, scope, completion evidence, and current generated inventory.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `node scripts/verify.mjs fast` | 0 | 170 | 170 | 0 | 0 | 94.6s; inventory, architecture, OpenAPI, model drift, Ruff, mypy, unit, contract, component, lint, typecheck, and production build passed |
| `uv run --frozen python -m scripts.run_coverage` | 0 | 147 | 145 | 0 | 2 | Backend 77.50% (2,239/2,889); 113 unit/contract plus 32 PostgreSQL integration passed; two approved ownership XFAIL; test DB dropped |
| `node node_modules/jest/bin/jest.js --runInBand --coverage` | 0 | 57 | 57 | 0 | 0 | 17 suites; frontend 28.59%; login BFF reached 100% line coverage |
| Independent changed-line calculation | 0 | 631 | 529 | 0 | 0 | 83.84% meaningful executable changed-line coverage, above the 80% policy |
| `uv run --frozen python -m scripts.run_migration_roundtrip` | 0 | 3 stages | 3 | 0 | 0 | Head → base → head; 14/1/14 tables; 7 audit indexes, 11 constraints, 2 triggers; UPDATE/DELETE/TRUNCATE rejected; test DB dropped |
| `node scripts/verify.mjs e2e-real` | 0 | 3 | 3 | 0 | 0 | Admin/student setup and real PostgreSQL student flow passed; owner/flake policy passed; test DB dropped |
| Independent migration, security, frontend, and completion reviews | 0 | 4 | 4 | 0 | 0 | No P1/P2 findings remained |
| `git diff --check` | 0 | — | — | 0 | 0 | No whitespace errors; only existing CRLF normalization warnings |

## Impact

- API/event/schema contract: Expected backend failures now return
  `{error_code, details, request_id}` and `X-Request-ID`; allowlisted protocol
  headers are preserved. The audit event contract and table are additive.
- Migration/data: New revision `b57c9a14d2e8`; downgrade removes only the new
  audit schema. No shared or non-test database was migrated.
- Security/ownership/tenant: Audit payloads fail closed on unknown actions,
  fields, sensitive keys/values, paths, IP addresses, or oversized data. Audit
  reads and business-action instrumentation are not exposed by this task.
- Dependency/toolchain: No new dependency. Configured mypy coverage now includes
  all new audit/privacy modules.

## Manual evidence

- Scenario: Real BFF login and student exam flow against disposable PostgreSQL.
- Result: 3/3 Playwright tests and ownership/flake policy passed after the POM
  selector was made exact; database cleanup was confirmed.
- Screenshot/trace: No layout change required a new visual baseline. Playwright
  failure artifacts proved the original selector ambiguity; the successful
  rerun produced no failure screenshot or trace.

## Risks and follow-up

- Known risks: DATA-002 action instrumentation is pending; two ownership cases
  remain expected failures until SEC-001/SEC-002; public material files and
  lifecycle authorization remain DATA-009; overall frontend legacy coverage is
  still low despite the non-regression baseline and 80% changed-code gate.
- Unverified items: First GitHub Actions run and branch-protection enforcement
  remain CI-002/CI-003/CI-010 review work. No production/shared database was
  exercised.
- Follow-up tasks: SEC-001/SEC-002, DATA-002–005, DATA-009, then governed AI
  work. Any future submission/grade purge requires a new ADR and owner approval.

## Rollback

- Code: Revert the DATA-001 commit and disable new event writes. The additive
  audit table may safely remain while application behavior is rolled back.
- Data: Do not downgrade a shared/live database as an application rollback.
  Preserve existing audit rows; use the verified downgrade only for disposable
  test databases.
