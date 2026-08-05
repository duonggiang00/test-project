# Change Contract: TEST-005 — Query-Budget Regression Tests

Risk level: L1
Owner: Primary Codex agent
Approval required: No

## Intent

Make important endpoint query budgets observable and prove that eager-loading behavior does not degrade into per-row queries as result size grows.

## Scope

- Preserve the existing maximum-query assertion for exam detail.
- Expose the observed query count from the shared PostgreSQL counter.
- Compare the same detail endpoint with 2 and 10 nested questions/options.

## Acceptance

- Both representative sizes return the expected response.
- Each request remains within the reviewed four-query ceiling.
- The larger response performs no more queries than the smaller response.
- The test runs only in the guarded PostgreSQL integration tier.
