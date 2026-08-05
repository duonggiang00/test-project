# Frontend Test Tiers

| Tier | Purpose | Command | External services |
|---|---|---|---|
| Unit | Pure hooks, stores, URL/error utilities | `npm run test:unit` | None |
| Component | DOM semantics and isolated interaction states | `npm run test:component` | None |
| Mocked E2E | Critical browser flow through UI and BFF-shaped mocks | `npm run test:e2e:mocked` | None |
| Real E2E | Auth, backend, and PostgreSQL smoke flow | `npm run test:e2e:real` | Backend + PostgreSQL |

The mocked suite must intercept every backend-bound request. Its fallback returns `501 UNHANDLED_MOCK_ROUTE`, never a fake success, so an incomplete mock fails at the consuming UI without contacting the backend.

The mocked PR matrix runs Chromium, Firefox, WebKit, and a mobile Chrome viewport. It uses one worker for deterministic Windows/CI parity and currently completes locally in 52 seconds.

The real suite runs Chromium through `backend/scripts/run_real_e2e.py`. The runner creates a guarded `_test` database, seeds only fixed test identities, starts the backend on isolated port 8765, executes login/topic/exam/question/submit/result/cleanup, and always stops the backend and drops its database. The current local run passes 3/3 tests and policy in 32.3 seconds.

Both Playwright suites retain screenshot/video on failure and trace on the single diagnostic retry. JSON/HTML reports and raw results are written under `frontend/reports/playwright/`.
