# Change Contract: TOOL-PYTEST-CACHE-001 and SEC-CSP-001

Risk level: L2
Owner: Primary coding agent
Approval required: No
Approval evidence: The project owner approved the staged remaining-work execution plan on 2026-08-25.

## Scope

- In scope:
  - Make the canonical backend coverage runner independent of `.pytest_cache` access.
  - Ensure coverage report directories exist before pytest writes JUnit/coverage artifacts.
  - Add regression tests for the runner command contract and failure propagation.
  - Generate a static-compatible CSP that keeps development `unsafe-eval` but removes it in production.
  - Remove obsolete Google Fonts, direct backend, OpenRouter, and wildcard image origins from CSP.
  - Add focused production/development policy tests and run the production build.
- Out of scope:
  - Nonce-based CSP or converting static pages to dynamic rendering.
  - Frontend language conversion and coverage-baseline increases.
  - Semantic RAG, provider changes, database changes, and external reports.

## Behavior

- Before:
  - Backend coverage can fail after successful tests when pytest cannot access a stale `.pytest_cache`.
  - The static CSP permits production `unsafe-eval`, remote font origins, direct backend/OpenRouter connections, and all HTTPS images.
- After:
  - Both backend pytest coverage phases explicitly disable the cache provider and create the report directory first.
  - Production allows only same-origin scripts/connections and local/blob/data assets; development alone retains `unsafe-eval`.
- Preserved invariants:
  - Coverage remains split into unit/contract plus guarded PostgreSQL integration phases.
  - Browser API traffic remains BFF-only.
  - Static App Router output remains supported; `unsafe-inline` is retained as the documented residual risk.

## Expected files and contracts

- Files/modules:
  - `backend/scripts/run_coverage.py`
  - `backend/tests/unit/test_run_coverage.py`
  - `frontend/src/lib/content-security-policy.ts`
  - `frontend/src/lib/content-security-policy.test.ts`
  - `frontend/next.config.ts`
  - workflow tracker, handoff, and generated inventory
- API/event/schema impact: None.
- Migration/data impact: None.
- Security/ownership/tenant impact: CSP is narrowed; authorization and ownership behavior are unchanged.

## Verification contract

- Targeted tests: coverage-runner unit tests and CSP unit tests.
- Static/type checks: scoped Ruff, frontend ESLint, TypeScript through production build, architecture guard.
- Integration/PostgreSQL checks: canonical coverage mode, including guarded PostgreSQL integration coverage.
- Build/E2E/visual checks: production build and mocked critical-flow E2E after CSP change.
- Manual verification: inspect the production and development header values; verify forbidden origins/tokens are absent from production.

## Rollback

- Code rollback: Revert this scoped commit. If a verified production dependency is blocked, restore only the minimum required directive/origin with a regression test.
- Data rollback: None.

## Assumptions and drift

- Verified assumptions:
  - Next.js 16 documentation states development requires `unsafe-eval`, while production does not.
  - The project uses local fonts and BFF-only browser transport.
  - The current App Router build emits static pages, so nonce CSP would materially change rendering.
- Unresolved assumptions: None.
- SPEC_DRIFT: None.
