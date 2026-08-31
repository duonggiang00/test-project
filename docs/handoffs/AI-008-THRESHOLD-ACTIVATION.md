# Handoff: AI-008 Threshold and RAG Activation

Status: DONE

Risk: L3 governed AI evaluation and retrieval activation

## Outcome

- Recorded owner approval of V8, the proposed thresholds, inactive cost gate,
  protected 20/40 schedule, CI implementation, and hybrid retrieval default.
- Added immutable V8 full-run and 20-case subset baseline integrity checks.
- Derived active 20-case ceilings from three reviewed runs: 9,562 input and
  1,703 output tokens; full-run limits remain 19,036 and 3,546.
- Added a protected candidate workflow: same-repository labeled PRs run 20
  cases; weekly/manual runs use 40; zero retries, no fallback, and provider
  routing are runtime-attested.
- Added a separate protected semantic attestation workflow bound to candidate,
  source commit, review commit, reviewer identity, and approved thresholds.
- Kept existing required check names unchanged; new checks remain non-required
  pending their first hosted proof. Cost remains null/inactive.
- Changed the evaluated retrieval default to hybrid; lexical and `RAG_ENABLED`
  remain immediate rollback controls.

## Repository setup

- Create protected environments `ai-regression` and `ai-regression-review`.
- Store `OPENROUTER_API_KEY` only in `ai-regression`; require a maintainer for
  environment approval and for the `ai-regression-approved` PR label.
- Independent reviews use the fixed path
  `backend/evals/ai-regression-reviews/<collection-run-id>.review.jsonl` on the
  supplied protected review commit.

## Verification

- Focused policy/collection/attestation tests: 23 passed.
- Ruff and mypy: passed on all changed Python boundaries.
- Baseline integrity: passed, 3 runs and fixed 20-case subset.
- Workflow YAML parse and fork/secret boundary assertions: passed.
- Backend manifest: 511 unit, 23 contract, and 170 PostgreSQL integration tests
  passed; `reports/agent-workflow/ai-008-threshold-final-backend-3/backend.json`.
- Fast manifest: 14/14 steps passed, including 511 backend unit, 23 contract,
  182 frontend unit tests, and production build;
  `reports/agent-workflow/ai-008-threshold-final-fast-3/fast.json`.
- Inventory and `git diff --check`: passed.
- Final independent L3 review: approved with no remaining P1/P2/P3 after
  provenance, artifact-digest, manifest, source-commit, and shell-boundary
  remediation; the reviewer also passed 43 focused tests, Ruff, and mypy.

## Rollback

Disable the non-required workflows, revert the activation commit, or set
`RAG_RETRIEVAL_MODE=lexical`. No database or data rollback is required.
