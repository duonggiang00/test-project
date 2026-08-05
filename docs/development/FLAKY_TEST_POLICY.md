# Flaky Test and Diagnostic Retry Policy

- CI permits at most one Playwright retry, only to collect trace evidence.
- A test that passes on retry is still a gate failure; the JSON policy checker rejects `flaky` status or any result with `retry > 0`.
- Every browser test has exactly one `@owner-*` tag. The current suite uses `@owner-frontend`.
- The owner must reproduce, identify the nondeterministic boundary, and fix or quarantine only with an approved blocker record.
- Increasing retries, weakening waits, or changing an assertion is not a flake fix.
- Failure artifacts retain JSON/HTML report, error context, screenshot, video, and first-retry trace for seven CI days.
