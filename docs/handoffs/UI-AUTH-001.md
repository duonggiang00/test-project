# Handoff: UI-AUTH-001 Square Brutalist Authentication

Status: REVIEW
Risk level: L2

## Outcome
- Summary: Replaced the duplicated rounded login and registration cards with a shared square black-and-white auth system, inline safe feedback, complete keyboard behavior, responsive reflow, and registration-success handoff to login.
- Requirements/task IDs: `UI-AUTH-001`.

## Files changed
- `frontend/src/app/(auth)/` — thin route wrappers and square session-checking state.
- `frontend/src/components/auth/` — shared auth shell, fields, password control, notice, submit action, login form, and registration form.
- `frontend/tests/component/auth-*.test.tsx` — error safety, validation, loading, payload, autocomplete, password visibility, and role redirect coverage.
- `frontend/tests/e2e/admin-flow.spec.ts` — cross-browser auth navigation, square/monochrome computed-style checks, keyboard focus, 360px/200% reflow, registration success, and preserved admin entry flow.
- `frontend/tests/e2e/admin-flow.spec.ts-snapshots/{login,register}-page-*.png` — approved-test baselines for Chromium, Firefox, WebKit, and mobile Chrome.
- `docs/plans/UI-AUTH-001_CHANGE_CONTRACT.md` — approved scope, invariants, verification, rollback, and drift.

## Verification
| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `jest --runInBand tests/component/auth-error-localization.test.tsx tests/component/auth-forms.test.tsx --coverage --collectCoverageFrom='src/components/auth/**/*.tsx'` | 0 | 10 | 10 | 0 | 0 | Auth components: 98.59% statements, 98.59% lines, 80.95% functions. |
| `node ../scripts/verify.mjs frontend` | 0 | 69 | 69 | 0 | 0 | Lint, unit tests, component tests, TypeScript, and 20-page production build passed; `VERIFY_OK mode=frontend`. |
| `playwright test --config=playwright.mocked.config.ts` | 0 | 16 | 16 | 0 | 0 | Chromium, Firefox, WebKit, and mobile Chrome passed, including the existing admin workflow. |
| `git diff --check` | 0 | — | — | — | — | No whitespace errors; Git emitted only an unrelated existing LF/CRLF warning for `frontend/.gitignore`. |

## Impact
- API/event/schema contract: no backend or BFF contract changes; `registered=1` is a frontend-only, non-security success marker removed from browser history after display.
- Migration/data: none.
- Security/ownership/tenant: unchanged; HttpOnly cookie, BFF boundary, backend authorization, and role redirects are preserved.
- Dependency/toolchain: no dependency or package-manager changes.

## Manual evidence
- Scenario: desktop and mobile login/registration visual review at normal scale.
- Result: one black identity panel plus one white form panel on desktop; single-column reflow on mobile; no rounded surfaces, gray paint, semantic color, soft shadow, duplicate form chrome, or dev badge in the baselines.
- Screenshot/trace: `frontend/tests/e2e/admin-flow.spec.ts-snapshots/login-page-chromium-win32.png`, `register-page-chromium-win32.png`, `login-page-mobile-chrome-win32.png`, and `register-page-mobile-chrome-win32.png` (with Firefox/WebKit equivalents).
- Scenario: 360px viewport with root text at 200%.
- Result: no auth element crosses the viewport; the registration notice was corrected with a shrinkable grid content column after the initial probe exposed overflow.

## Risks and follow-up
- Known risks: none in the implemented auth UI scope.
- Unverified items: independent L2 diff review and project-owner visual acceptance remain pending; implementation and executable gates are complete.
- Follow-up tasks: resolve the pre-existing global font drift by bundling an approved local font through `next/font/local` and removing the remote Material Symbols dependency in a separately approved task.

## Rollback
- Code: restore the three auth route files and remove `frontend/src/components/auth/`, the focused tests, and the eight auth visual baselines.
- Data: none.
