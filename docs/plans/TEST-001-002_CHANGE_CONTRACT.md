# Change Contract: TEST-001 and TEST-002 — Coverage Baseline and Regression Gate

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Intent

- Measure reproducible backend and frontend line-coverage baselines.
- Prevent either repository-wide baseline from decreasing silently.
- Require approximately 80% line coverage for executable lines changed from a CI-provided base commit.

## Scope

- The backend coverage run executes unit tests in their normal configuration process, then PostgreSQL integration tests in an isolated `ENV=test` process, and combines both coverage datasets.
- The frontend coverage run instruments all TypeScript/TSX files under `frontend/src`, not only imported files.
- Generated reports remain ignored build artifacts; the reviewed numeric baseline is committed.

## Compatibility and safety

- Existing unit, integration, and frontend commands retain their behavior.
- The guarded database manager still refuses remote, non-`_test`, development, admin, or pre-existing targets and always drops only the database it created.
- The policy does not impose an immediate 80% repository-wide threshold.
- A baseline reduction is never an automatic fix; it requires evidence that the baseline/spec is wrong and review of the numeric change.

## Verification

- Full backend coverage run and guaranteed test-database cleanup.
- Full-source frontend coverage run.
- Baseline check passes at the recorded percentages.
- Deliberately elevated baseline fixture fails the checker.
- Changed-code calculation is exercised against a known Git base when available.
