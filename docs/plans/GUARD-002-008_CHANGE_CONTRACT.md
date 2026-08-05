# Change Contract: GUARD-002 through GUARD-008 — Anti-Pattern Gate

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Intent

Convert critical backend, frontend, API-route, and brutalist design rules into a deterministic fast-gate failure without requiring all legacy debt to be removed in one change.

## Baseline policy

- Existing findings are committed as normalized fingerprints.
- Removing debt is always allowed.
- Every new or duplicated fingerprint fails.
- Regenerating the baseline is not an accepted fix for a violation.

## Evidence

- Good fixtures produce zero findings.
- Bad fixtures exercise 17 rule families.
- A temporary source probe using `Session.query()` failed the live baseline check.
- The clean current tree passes with 247 recorded legacy findings.
