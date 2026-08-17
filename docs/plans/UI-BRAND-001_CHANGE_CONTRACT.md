# Change Contract: UI-BRAND-001 PlayStudy branding

Risk level: L1
Owner: Codex primary agent
Approval required: No additional approval
Approval evidence: Owner-approved implementation plan in the active task.

## Scope
- In scope: Replace QuizBuddy branding on the landing page and student header; align the auth shell; set PlayStudy metadata; replace the favicon with a black-and-white `P` monogram; add focused tests.
- Out of scope: Authentication behavior, routing, permissions, backend APIs, reports, historical documentation, and unrelated visual-system cleanup.

## Behavior
- Before: The landing page and student header display QuizBuddy branding, the auth shell uses a separate PlayStudy text treatment, and browser metadata uses the Next.js starter defaults.
- After: All active frontend branding uses one square PlayStudy `P` monogram and `PLAYSTUDY` wordmark; browser metadata and favicon identify PlayStudy.
- Preserved invariants: Existing links, auth redirects, BFF behavior, state management, and responsive page structures remain unchanged.

## Expected files and contracts
- Files/modules: Shared branding component, landing page, student header, auth shell, root metadata, favicon, focused frontend tests.
- API/event/schema impact: None.
- Migration/data impact: None.
- Security/ownership/tenant impact: None.

## Verification contract
- Targeted tests: Branding component and active landing/auth/student surfaces.
- Static/type checks: ESLint and TypeScript through the production build.
- Integration/PostgreSQL checks: Not applicable.
- Build/E2E/visual checks: Next.js production build and desktop/mobile browser screenshots for affected surfaces.
- Manual verification: Confirm square corners, black/white-only brand treatment, correct accessible names, browser title, favicon, and zero active QuizBuddy references.

## Rollback
- Code rollback: Revert the scoped branding files and restore the previous favicon.
- Data rollback: Not applicable.

## Assumptions and drift
- Verified assumptions: `admin`, `teacher`, and `student` behavior is unchanged; active legacy brand references are limited to the landing page and student header; the auth shell already uses the PlayStudy name.
- Unresolved assumptions: None.
- SPEC_DRIFT: The pre-existing remote Material Symbols font and unrelated gray UI tokens are outside this approved branding task.
