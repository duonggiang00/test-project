# Change Contract: GUARD-001 — Python Lint and Type Baseline

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Intent

- Run Ruff syntax/name correctness checks across backend application, scripts, and tests.
- Run mypy on the typed configuration, security, and guarded runner boundary.
- Put both commands in local and CI fast verification.

## Baseline policy

The initial mypy scope is explicit and honest; untyped application services are not counted as passing type checks. New typed modules should be added to the scope. Broad `ignore_errors` modules and blanket error-code suppression are not accepted expansion strategies.
