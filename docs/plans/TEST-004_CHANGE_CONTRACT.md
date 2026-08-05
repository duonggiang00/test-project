# Change Contract: TEST-004 — Ownership Negative-Test Matrix

Risk level: L1 tests; target implementation remains L3
Owner: Primary Codex agent
Approval required: No for tests; yes for SEC-001/002 implementation

## Intent

Turn the approved anonymous/student/owner/non-owner/admin policy into executable evidence without silently changing current authentication or authorization behavior.

## Scope

- Add a passing five-actor matrix for exam update.
- Add strict expected-failure regression cases for confirmed exam bulk-assignment and material-detail tenant gaps.
- Publish a compact resource/action matrix linked to the governing SEC tasks.

## Safety boundary

This change does not fix RBAC, add ownership fields, or change API responses. Those changes require an approved security change contract and independent review. Expected failures are not considered passing security coverage and keep TEST-004 blocked until the gaps are closed.
