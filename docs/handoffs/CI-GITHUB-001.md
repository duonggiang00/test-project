# Handoff: CI-GITHUB-001 — Hosted Verification and Main Protection

Status: DONE
Risk level: L2 repository-governance change

## Outcome

- Summary: Published the repository workflow, repaired every hosted-only CI defect without weakening gates, added reviewed GitHub-runner visual baselines, completed the first green push and pull-request executions, and applied the declared `main` protection policy.
- Requirements/task IDs: CI-002, CI-003, CI-005, CI-006, CI-010.

## Files changed

- `.github/workflows/ci.yml` — use resolvable action releases and create ignored profile-specific CI environment files.
- `scripts/create-ci-env.mjs` — derive checked fast/PostgreSQL CI environments from `.env.example` without process-level database-variable contamination.
- `scripts/project-inventory.mjs` — make inventory hashing cross-platform and exclude ignored Playwright authentication state.
- `scripts/database-model-drift.mjs` and `scripts/openapi-contract.mjs` — isolate application-importing static introspection settings from the parent fast-test process.
- `frontend/tests/e2e/admin-flow.spec.ts` — preserve exact keyboard-order assertions across Windows and Linux WebKit conventions.
- `frontend/tests/e2e/admin-flow.spec.ts-snapshots/*-linux.png` — provide 27 reviewed Ubuntu-runner baselines for Chromium, Firefox, WebKit, and mobile Chrome.
- `docs/plans/CI-GITHUB-001_CHANGE_CONTRACT.md` — record approved scope and execution evidence.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — track completion only after hosted evidence exists.
- `docs/handoffs/CI-GITHUB-001.md` — preserve commands, hosted links, impact, risks, and rollback guidance.

## Verification

| Command or hosted check | Exit/conclusion | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `node scripts/create-ci-env.mjs check` | 0 | 2 profiles | 2 | 0 | 0 | Fast and PostgreSQL profiles satisfy the checked contract. |
| `node scripts/check-github-branch-policy.mjs` | 0 | 3 required contexts | 3 | 0 | 0 | Policy and workflow job names agree. |
| pre-commit canonical fast verification at `48f3d48` | 0 | 487 backend/frontend tests plus build | 487 | 0 | 0 | Inventory, architecture, lint, type, unit, and production-build gates passed locally. |
| `node scripts/verify.mjs e2e-mocked` | 0 | 28 tests | 28 | 0 | 0 | Windows Chromium, Firefox, WebKit, mobile Chrome, and owner/flake policy passed. |
| [GitHub push run 32831201837](https://github.com/duonggiang00/test-project/actions/runs/32831201837) | success | 5 jobs | 3 | 0 | 2 | Fast, PostgreSQL integration/Alembic, and real E2E passed; PR-only jobs skipped as designed. |
| [GitHub PR run 32837826190](https://github.com/duonggiang00/test-project/actions/runs/32837826190) | success | 5 jobs | 3 | 0 | 2 | Fast, coverage regression, and the 28-test mocked browser matrix passed; push-only jobs skipped as designed. |
| `main` protection PUT response/read-back | success | 3 contexts plus policy flags | 6 | 0 | 0 | Exact contexts are required with `strict=true`; force pushes and deletion are disabled. |

## Impact

- API/event/schema contract: None.
- Migration/data: No application migration or shared data operation. GitHub PostgreSQL service containers and ignored test environment files are ephemeral.
- Security/ownership/tenant: No application authorization change. No repository secret was added, printed, or committed.
- Dependency/toolchain: GitHub action references now resolve to official current releases; application dependency manifests are unchanged.

## Manual evidence

- Scenario: Push `main` and inspect every hosted job rather than relying only on the aggregate workflow conclusion.
- Result: Push and pull-request job sets passed. Before remediation, PR #1 reported `mergeable_state=unstable` while `Mocked browser matrix` failed and Coverage was pending under the active required-check rule; the protected merge state cleared only after all required checks passed.
- Screenshot/trace: GitHub-hosted run/job links are retained in this handoff and the change contract.

## Risks and follow-up

- Known risks: The declared policy does not require administrator enforcement, so repository administrators retain GitHub's explicit bypass capability; ordinary protected merges require all three checks.
- Unverified items: None for CI-002, CI-003, CI-005, CI-006, or the declared CI-010 policy.
- Follow-up tasks: Keep GitHub action releases and Linux visual baselines current through reviewed pull requests; do not regenerate baselines automatically in the required check.

## Rollback

- Code: Revert the relevant CI commits with new commits; do not rewrite published history.
- Data: No persistent application data rollback is required. Restore the prior GitHub branch rule through the same authenticated interface if protection must be rolled back.
