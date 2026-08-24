# Change Contract: ANTI-NODB-001 No-database anti-pattern remediation

Risk level: L2
Owner: Primary implementation agent
Approval required: No additional approval
Approval evidence: The owner explicitly directed implementation of the recommended no-database track on 2026-08-24.

## Scope

- In scope: stabilize the current review-stage worktree; improve architecture-guard precision; remove orphan workspace test code; replace remote fonts and Material Symbols; normalize the active design system to approved black-and-white styling; keep all newly written or modified UI copy in English; and perform behavior-preserving frontend/pure-logic refactors that can be verified without a database server.
- Copy boundary: a survey found 456 pre-existing non-ASCII source lines across legacy frontend screens. Translating that independent product-copy backlog is not required to remove the code/design anti-patterns and is deferred to a dedicated copy-review task.
- Out of scope: Alembic migrations, authentication/session lifecycle, authorization or ownership behavior, query-shape changes, PostgreSQL concurrency, audit-trigger behavior, data backfills, and real-backend E2E.

## Behavior

- Before: the worktree contains several uncommitted review-stage tasks; the guard contains known false positives and does not inspect CSS; the root layout loads a remote icon font; legacy colored CSS and Material Symbols remain; one ad-hoc browser script bypasses the formal test harness.
- After: existing work is checkpointed without being misreported as PostgreSQL-verified; guard findings are actionable and monotonically reduced; the frontend uses bundled IBM Plex Mono and Lucide icons; active UI styling is strict black and white; new or modified copy is English; orphan test code is removed or represented by formal tests.
- Preserved invariants: public API, database schema, authentication, authorization, ownership, route URLs, BFF-only transport, and user-flow behavior remain unchanged.

## Expected files and contracts

- Files/modules: architecture guard and fixtures; frontend root layout, global CSS, shared/domain UI components, frontend tests; task contracts, handoffs, and generated inventory.
- API/event/schema impact: none.
- Migration/data impact: none.
- Security/ownership/tenant impact: none; database-sensitive tasks remain `REVIEW` until PostgreSQL evidence exists.

## Verification contract

- Targeted tests: architecture fixtures, relevant Jest unit/component suites, and pure Python unit tests for any touched database-agnostic logic.
- Static/type checks: architecture guard, Ruff, mypy, ESLint, TypeScript production build, generated inventory/OpenAPI checks.
- Integration/PostgreSQL checks: not run by this task; no database-sensitive behavior may be marked complete.
- Build/E2E/visual checks: production build and mocked Playwright visual/navigation suites when browser binaries are available.
- Manual verification: inspect desktop/mobile black-and-white snapshots, keyboard focus, English UI strings, font loading, and final scoped diffs.

## Rollback

- Code rollback: revert each no-database checkpoint independently.
- Data rollback: not applicable.

## Assumptions and drift

- Verified assumptions: `node scripts/verify.mjs fast` passes without PostgreSQL; the PostgreSQL integration runner is blocked because no local server is installed; Lucide is already installed; no repository-owned font asset exists.
- Unresolved assumptions: none for the no-database scope. Chromium, Firefox, WebKit, and mobile Chrome are installed and verified locally.
- SPEC_DRIFT: the current remote Material Symbols link and colored CSS conflict with ADR-0005; database-related drift is explicitly deferred.
