# Frontend Test Rules

Apply this file to changes under `frontend/tests/` and to colocated frontend test files.

- Test user-observable behavior and public hook/service contracts.
- Do not weaken assertions or replace real behavior with a mock merely to make a test pass.
- Keep mocked-network E2E and real-backend E2E as distinct suites with explicit commands.
- Pull-request E2E uses deterministic mocked responses and must not modify a developer/shared database.
- Main/nightly smoke E2E uses an isolated backend and PostgreSQL dataset.
- Start navigation tests from the intended dashboard/home entry point rather than opening only the target URL.
- Cover loading, empty, error, disabled, cache-update/rollback, and authorization redirect states as applicable.
- Prefer role, label, and visible text locators. Use stable test IDs only when semantic locators are insufficient.
- Do not use arbitrary timeouts; wait for observable state.
- Capture trace and screenshot on failure. A single retry is diagnostic and does not erase flaky status.
- Visual regression baselines must be reviewed at desktop and mobile sizes and preserve strict black/white semantics.
- Critical browser coverage includes Chromium, Firefox, WebKit, and mobile projects.
- Report collected, passed, failed, skipped, retried, and flaky counts.
