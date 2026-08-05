# Change Contract: TEST-003 — Backend Test Tiers

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Intent

Make backend unit, API contract, and PostgreSQL integration suites independently selectable and give each tier an explicit executable contract.

## Tier boundaries

- `unit`: isolated logic and safety tests; no PostgreSQL behavior dependency.
- `contract`: OpenAPI/schema/error-envelope checks; no PostgreSQL behavior dependency.
- `integration`: application behavior that uses the guarded PostgreSQL `_test` lifecycle.

Directory-based marker assignment is centralized in `backend/tests/conftest.py`. A test outside `unit/` or `contract/` remains integration by default so a misplaced database test cannot silently enter the fast suite.

## Verification

- `pytest --collect-only -m unit`, `contract`, and `integration` select disjoint sets whose union equals the full collection.
- The canonical fast gate runs unit and contract tiers.
- The canonical backend gate runs unit, contract, then PostgreSQL integration.
- Coverage combines unit + contract data with the isolated integration process.
