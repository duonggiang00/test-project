# Change Contract: CI-005/007/008/009 and TEST-006 — Browser Test Architecture

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Intent

- Make the existing admin critical flow truly backend-independent for pull requests.
- Separate unit, component, mocked E2E, and real-backend E2E entry points.
- Exercise Chromium, Firefox, WebKit, and mobile viewport behavior.
- Preserve useful failure artifacts without allowing a retry to hide flakes.

## Boundaries

- Real E2E uses a guarded local `_test` database, seeds only fixed test identities, and always terminates the backend and drops the database it created.
- Mocked BFF requests use explicit response contracts and a failing `501` fallback.
- Browser tests carry a single owner tag and use one diagnostic retry in CI.

## Evidence

- Component tier passes independently.
- Mocked admin create/delete flow passes all four projects locally.
- Real login/topic/exam/question/student-submit/result/cleanup flow passes against the guarded PostgreSQL runner.
- Report policy accepts the clean matrix and rejects flaky/retried/unowned results.
- CI uploads Playwright reports, screenshots, videos, traces, and error context on failure.
