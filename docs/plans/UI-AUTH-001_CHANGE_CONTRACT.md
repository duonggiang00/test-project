# Change Contract: UI-AUTH-001 Square Brutalist Authentication

Risk level: L2
Owner: Codex primary agent
Approval required: Yes
Approval evidence: Project owner explicitly requested implementation of the approved login and registration redesign plan on 2026-08-15.

## Scope
- In scope: redesign the login, registration, and auth-session loading surfaces; add auth-specific presentation components; add component, E2E, accessibility, responsive, and visual checks.
- Out of scope: backend authentication behavior, BFF cookie semantics, token storage, authorization, role policy, API/schema changes, password-reset production behavior, global primitive redesign, and global font migration.

## Behavior
- Before: login and registration duplicate card/form styling, inherit rounded primitive styles, rely on toast-only error feedback, and lack a shared responsive auth identity shell.
- After: both routes use a shared two-panel square brutalist shell on desktop and a single-column layout on mobile; all auth controls use only black and white with zero radius; validation and safe backend errors are rendered next to the form; registration identifies self-service accounts as students.
- Preserved invariants: login payload and remember-me behavior remain unchanged; registration sends only `email`, `password`, and `full_name`; cookies remain BFF-managed; admin/teacher redirect to `/dashboard`; students redirect to `/student/home`; unauthenticated users remain on `/login`.

## Expected files and contracts
- Files/modules: `frontend/src/app/(auth)/`, new `frontend/src/components/auth/`, focused auth component/E2E tests, and approved visual baselines.
- API/event/schema impact: none. A `registered=1` query marker is a frontend-only, non-security success notice and is ignored for authentication decisions.
- Migration/data impact: none.
- Security/ownership/tenant impact: none; backend authorization and the BFF boundary remain authoritative.

## Verification contract
- Targeted tests: auth component behavior, safe error localization, field validation, password visibility, remember-me, duplicate-submit prevention, registration payload, success notice, and role redirects.
- Static/type checks: ESLint and Next.js production build.
- Integration/PostgreSQL checks: not required because no backend, query, or persistence behavior changes.
- Build/E2E/visual checks: mocked auth navigation, desktop/mobile screenshots, zero-radius and black/white computed-style assertions, Chromium/Firefox/WebKit coverage when the installed browsers are available.
- Manual verification: keyboard order, visible focus, 360px layout, 200% zoom, and password-manager/autofill-compatible field semantics.

## Rollback
- Code rollback: remove the auth-specific components and tests, then restore the three auth route files.
- Data rollback: none.

## Assumptions and drift
- Verified assumptions: self-registration creates a student account; remember-me controls session versus seven-day cookies; existing login and registration transport functions already use the approved BFF/proxy boundary.
- Unresolved assumptions: none within this task.
- SPEC_DRIFT: the repository currently has no local font asset wired through `next/font/local`, and the root layout still loads a remote Material Symbols font. This task does not expand into the global font migration approved as separate work.
