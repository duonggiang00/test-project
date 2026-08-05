# Change Contract: TOOL-005 and TOOL-006 — Environment and Verification Entry Points

Risk level: L1  
Owner: Primary Codex agent  
Approval required: No  
Approval evidence: The owner approved execution of the canonical optimization plan.

## Scope

- In scope:
  - Make the canonical root `.env.example` match settings consumed by backend and frontend server code.
  - Resolve the backend env file from the repository root independently of the current working directory.
  - Replace public-prefixed backend URL configuration with a server-only canonical name while retaining a temporary compatibility fallback.
  - Add deterministic, cross-platform verification entry points implemented with Node and existing project tooling.
  - Ignore local package-manager cache output.
- Out of scope:
  - Authentication lifecycle, cookie names, token rotation, or CSRF behavior.
  - Database schema or migrations.
  - PostgreSQL provisioning and suite isolation (`TOOL-008`).
  - CI workflow gates (`CI-002` onward).
  - Rewriting existing integration or E2E tests.

## Behavior

- Before:
  - Backend env loading depends on the process working directory.
  - `.env.example` documents unused and conflicting variable names.
  - BFF server code reads a `NEXT_PUBLIC_*` backend URL.
  - Verification requires unrelated one-off commands and a Windows-only batch wrapper.
- After:
  - Backend settings load the repository-root `.env` consistently.
  - The example documents only supported canonical variables and safe placeholders.
  - BFF code prefers `BACKEND_API_URL` and temporarily accepts `NEXT_PUBLIC_API_URL` for compatibility.
  - `node scripts/verify.mjs <env|fast|backend|frontend|integration|e2e|all>` provides shared Windows/CI entry points.
- Preserved invariants:
  - PostgreSQL remains canonical.
  - Existing component-based PostgreSQL settings remain supported.
  - Existing local environments using `NEXT_PUBLIC_API_URL` continue to work during migration.
  - Backend authorization and frontend cookie behavior are unchanged.

## Expected files and contracts

- Files/modules:
  - `.env.example`, `.gitignore`
  - `backend/app/core/config.py`, `backend/app/main.py`, backend config tests
  - Frontend server URL helper, BFF route handlers, `next.config.ts`, helper tests
  - `scripts/verify.mjs`, `scripts/validate-env-example.mjs`
  - Development verification documentation and the optimization tracker
- API/event/schema impact: None.
- Migration/data impact: None.
- Security/ownership/tenant impact: No authorization change; the canonical backend URL is no longer intentionally exposed through a public-prefixed variable.

## Verification contract

- Targeted tests:
  - Backend settings unit tests.
  - Frontend backend-URL helper unit tests.
  - Env-example contract validator.
- Static/type checks:
  - Node syntax check for orchestration scripts.
  - Frontend lint and build through the shared entry point.
- Integration/PostgreSQL checks:
  - Run the current backend suite and report its existing SlowAPI failure separately.
- Build/E2E/visual checks:
  - Frontend build through the shared frontend entry point.
  - Use the installed Next.js-supported `--webpack` build mode when the default Turbopack build exceeds the approved Windows gate budget.
  - E2E remains a callable entry point; browser execution is not required for this config-only change.
- Manual verification:
  - Invoke each non-destructive entry point or its list/dry discovery path and inspect exact output.

## Rollback

- Code rollback: Revert the scoped files; the compatibility fallback prevents an atomic deployment requirement.
- Data rollback: Not applicable.

## Assumptions and drift

- Verified assumptions:
  - The root `.env` contains both the legacy frontend URL and PostgreSQL component keys.
  - Frontend BFF routes are the only runtime consumers of the legacy frontend URL variable.
  - Node 22 is the declared local version and uv is installed.
- Unresolved assumptions:
  - PostgreSQL test database isolation is deferred to `TOOL-008`.
  - The current frontend E2E setup still depends on a live backend for authentication.
- SPEC_DRIFT:
  - The existing Playwright test labeled `MOCKED` still uses live-backend global authentication.
  - The existing CSP permits remote fonts and direct backend/OpenRouter connections despite the canonical local-font and BFF-only policies; security-header changes are outside this task.
