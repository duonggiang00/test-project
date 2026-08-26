# Handoff: UI-LANGUAGE-001 and TEST-FE-COVERAGE-001

Status: DONE
Risk level: L2

## Outcome

- Summary: Converted the 37 identified executable frontend files from hard-coded Vietnamese presentation copy/comments to English across four bounded waves. Added six behavior-oriented component/hook suites and raised honest all-source frontend line coverage from 61.25% to 76.97%.
- Requirements/task IDs: `UI-LANGUAGE-001`, `TEST-FE-COVERAGE-001`.

## Files changed

- `frontend/src/` — English UI copy, accessibility labels, safe error translations, and implementation comments; application behavior and data boundaries are unchanged.
- `frontend/tests/component/` — translated assertions plus six new behavior-oriented suites for hooks, results, students, submissions, topics, and translated critical UI contracts.
- `frontend/tests/e2e/` — English semantic locators and reviewed Windows/Linux visual baselines.
- `config/coverage-baseline.json` — frontend line floor raised to the measured 76.97%; the 80% changed-code target is unchanged.
- `docs/generated/project-inventory.json`, tracker, Change Contract, and this handoff — refreshed completion evidence.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `rg -n "[À-ỹ]" frontend/src` | 1 | 0 matches | — | — | — | No unintended Vietnamese UI/comment source remains |
| Focused reviewer-remediation tests | 0 | 9 | 9 | 0 | 0 | Semantic pagination and translated UI contracts pass |
| Full-source Jest coverage | 0 | 182 | 182 | 0 | 0 | 37 suites; 76.97% lines (`10,588/13,756`) |
| `$env:COVERAGE_BASE_SHA='WORKTREE'; node scripts/check-coverage.mjs check` | 0 | 459 changed lines | 377 | 0 | 82 uncovered | `COVERAGE_OK`; changed-line coverage is 82.14% against an unchanged 80% target |
| `npm run lint` | 0 | — | — | — | — | ESLint passes |
| `node scripts/architecture-guard.mjs check` | 0 | — | — | — | — | `current=0 baseline=0 waivers=1` |
| `npm run build` | 0 | 23 routes | 23 | 0 | 0 | Production build and TypeScript pass |
| `node node_modules/@playwright/test/cli.js test --config=playwright.mocked.config.ts` (Windows) | 0 | 28 | 28 | 0 | 0 | Chromium, Firefox, WebKit, and mobile Chrome pass without updating snapshots |
| Same Playwright command in an isolated Node 22.17.0 WSL/Ubuntu frontend harness | 0 | 28 | 28 | 0 | 0 | Linux baselines pass without updating snapshots after Playwright runtime dependencies were installed |
| Targeted AI review flow after guardrail visual remediation (Windows and Linux) | 0 | 8 | 8 | 0 | 0 | Four browser projects per platform pass without snapshot updates; persistent warning remains unobscured |
| `node scripts/verify.mjs fast` | 0 | 328 backend unit + 24 contract + 65 frontend unit + 117 component | 534 | 0 | 0 | `VERIFY_OK mode=fast`; environment, branch policy, DB drift, inventory, architecture, OpenAPI, lint/type, tests, and production build pass |
| `git diff --check` | 0 | — | — | — | — | No whitespace errors after reviewer fixes |

## Impact

- API/event/schema contract: None.
- Migration/data: None.
- Security/ownership/tenant: None; backend enforcement and BFF boundaries are unchanged.
- Dependency/toolchain: No dependency added.

## Manual evidence

- Scenario: Reviewed representative public landing, authentication, admin/AI review, Exam Details/Builder, and student branding surfaces at desktop and mobile widths.
- Result: English text remains readable without new overflow; strict black/white hierarchy, hard borders, focus semantics, and responsive stacking are preserved. Transient AI upload/progress toasts are dismissed before visual capture so the persistent safety warning is fully visible. The mobile AI capture retains the test flow's internal scroll position but keeps review actions and content legible.
- Windows screenshots: `frontend/tests/e2e/admin-flow.spec.ts-snapshots/landing-header-chromium-win32.png`, `login-page-chromium-win32.png`, `exam-builder-empty-chromium-win32.png`, `exam-builder-empty-mobile-chrome-win32.png`, `student-header-brand-mobile-chrome-win32.png`, and `frontend/tests/e2e/ai-review-flow.spec.ts-snapshots/ai-review-awaiting-review-{chromium,mobile-chrome}-win32.png`.
- Linux evidence: the corresponding `*-linux.png` baselines pass the full mocked E2E matrix in WSL/Ubuntu with the repository's Playwright browser versions.

## Risks and follow-up

- Known risks: Copy is currently hard-coded English rather than an internationalization catalog; localization architecture remains outside scope.
- Unverified items: GitHub-hosted coverage changed-line evaluation requires a real PR base SHA.
- Follow-up tasks: AI-006 through AI-008, then RAG-SEMANTIC-001.
- Independent review: APPROVED with no remaining P1/P2/P3 findings. The first review found a failing changed-line gate, two meaning-changing translations, inaccessible pagination, premature completion evidence, and incomplete visual evidence. Re-review found a desktop AI guardrail obscured by transient toasts. All findings are remediated and verified.

## Rollback

- Code: Revert the scoped task commit so UI copy, assertions, screenshots, and coverage baseline move together.
- Data: Not applicable.
