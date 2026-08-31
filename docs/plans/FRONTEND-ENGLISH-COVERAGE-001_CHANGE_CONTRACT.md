# Change Contract: UI-LANGUAGE-001 and TEST-FE-COVERAGE-001

Risk level: L2
Owner: Primary coding agent
Approval required: No
Approval evidence: The project owner approved the four-wave frontend language and coverage plan on 2026-08-25.

## Scope

- In scope:
  - Convert hard-coded Vietnamese UI copy, accessibility labels, error translations, and implementation comments in `frontend/src` to English.
  - Update assertions and browser locators that represent changed UI contracts.
  - Deliver four bounded waves: public/auth, admin/AI, exam, and student/shared.
  - Add behavior-oriented tests for translated critical modules and raise the honest all-source frontend coverage baseline.
- Out of scope:
  - Translating user-authored/domain fixture content whose language is the behavior under test.
  - Visual redesign, route changes, backend behavior, database changes, AI evaluation, or semantic retrieval.
  - Weakening coverage policy, excluding executable files, or adding tests that assert only implementation details.

## Behavior

- Before:
  - Thirty-seven executable frontend source files contain Vietnamese UI text or comments despite the workspace English-language contract.
  - Global all-source frontend line coverage was 61.25% before this task.
- After:
  - `frontend/src` contains no unintended Vietnamese UI/comment strings.
  - Existing flows expose the same behavior with English text and accessible names.
  - Critical translated modules receive meaningful state/interaction coverage; the measured global baseline is 76.97%, exceeding the 71.25% task target without exclusions or weakened assertions.
- Preserved invariants:
  - Routes, BFF requests, permissions, state transitions, and backend error-code handling remain unchanged.
  - Strict black-and-white brutalist layout and keyboard/accessibility behavior remain unchanged.
  - Tests may retain Vietnamese only as explicit user-authored/domain data fixtures.

## Expected files and contracts

- Files/modules: the 37 surveyed `frontend/src` files, paired frontend tests/E2E locators, coverage baseline, generated inventory, tracker, and handoff.
- API/event/schema impact: None.
- Migration/data impact: None.
- Security/ownership/tenant impact: None; backend authorization remains authoritative.

## Verification contract

- Targeted tests: tests paired with each wave and a source scan for unintended Vietnamese text/comments.
- Static/type checks: frontend ESLint, architecture/design guard, production TypeScript build.
- Integration/PostgreSQL checks: Not required for copy-only frontend behavior; no API/database contract changes.
- Build/E2E/visual checks: production build and affected mocked browser flows across all configured projects; update and inspect platform-specific visual baselines when translated copy changes rendered output.
- Manual verification: inspect representative public/auth, admin/AI, exam, and student surfaces in the production browser flow.

## Rollback

- Code rollback: Revert the affected wave commit; do not restore only test assertions without their UI copy.
- Data rollback: None.

## Assumptions and drift

- Verified assumptions:
  - The workspace policy requires English code, comments, documentation, UI text, and error translations.
  - Existing Vietnamese strings are hard-coded presentation copy, not a localization catalog.
  - Current global frontend line coverage is 76.97% from the all-source coverage run (`10,588/13,756` lines).
  - Changed executable lines pass the repository-supported `WORKTREE` gate at 82.14% (`377/459`), above the unchanged 80% target.
  - The source scan covers the 37 identified executable files and returns zero unintended Vietnamese UI/comment matches.
  - The full 28-case mocked E2E matrix passes without snapshot updates on Windows and Linux across Chromium, Firefox, WebKit, and mobile Chrome.
- Unresolved assumptions: None. Vietnamese retained in tests is explicit user-authored/domain fixture data, not product presentation copy.
- SPEC_DRIFT: Live UI language conflicts with the workspace English-language contract; this task resolves that drift without changing product behavior.
