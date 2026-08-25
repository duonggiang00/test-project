# Handoff: CI-GITHUB-001 — Hosted Verification and Main Protection

Status: REVIEW
Risk level: L2 repository-governance change

## Outcome

- Summary: Published the repository workflow to GitHub, repaired the Linux-hosted CI bootstrap/configuration defects exposed by the first runs, and started collecting hosted push and pull-request evidence before applying the declared `main` protection policy.
- Requirements/task IDs: CI-002, CI-003, CI-005, CI-006, CI-010.

## Files changed

- `.github/workflows/ci.yml` — use resolvable action releases and create ignored profile-specific CI environment files.
- `scripts/create-ci-env.mjs` — derive checked fast/PostgreSQL CI environments from `.env.example` without process-level database-variable contamination.
- `scripts/generate-project-inventory.mjs` — make inventory hashing cross-platform and exclude ignored Playwright authentication state.
- `scripts/verify-fast-gates.mjs` — isolate application-importing static introspection settings from the parent fast-test process.
- `docs/plans/CI-GITHUB-001_CHANGE_CONTRACT.md` — record approved scope and execution evidence.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — track completion only after hosted evidence exists.
- `docs/handoffs/CI-GITHUB-001.md` — preserve commands, hosted links, impact, risks, and rollback guidance.

## Verification

| Command or hosted check | Exit/conclusion | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `node scripts/create-ci-env.mjs check` | 0 | 2 profiles | 2 | 0 | 0 | Fast and PostgreSQL profiles satisfy the checked contract. |
| `node scripts/check-github-branch-policy.mjs` | 0 | 3 required contexts | 3 | 0 | 0 | Policy and workflow job names agree. |
| pre-commit canonical fast verification at `2a74828` | 0 | 487 backend/frontend tests plus build | 487 | 0 | 0 | Inventory, architecture, lint, type, unit, and production-build gates passed locally. |
| [GitHub push run 32831201837](https://github.com/duonggiang00/test-project/actions/runs/32831201837) | In progress | 5 jobs | 2 | 0 | 2 | `Fast verification` and `Real backend smoke E2E` passed; the PostgreSQL job is still running; PR-only jobs skipped as designed. |

## Impact

- API/event/schema contract: None.
- Migration/data: No application migration or shared data operation. GitHub PostgreSQL service containers and ignored test environment files are ephemeral.
- Security/ownership/tenant: No application authorization change. No repository secret was added, printed, or committed.
- Dependency/toolchain: GitHub action references now resolve to official current releases; application dependency manifests are unchanged.

## Manual evidence

- Scenario: Push `main` and inspect every hosted job rather than relying only on the aggregate workflow conclusion.
- Result: The current push run has passed Fast and real-backend E2E; remaining PostgreSQL and pull-request/protection evidence is still required.
- Screenshot/trace: GitHub-hosted run/job links are retained in this handoff and the change contract.

## Risks and follow-up

- Known risks: Branch protection must not be applied until GitHub has observed all three exact required pull-request check contexts.
- Unverified items: First successful PostgreSQL integration run, all three pull-request jobs, exact remote protection read-back, and negative merge-block evidence.
- Follow-up tasks: Open the probe pull request, resolve any hosted-only defects without weakening checks, apply the declared policy, read it back, and verify merge enforcement.

## Rollback

- Code: Revert the relevant CI commits with new commits; do not rewrite published history.
- Data: No persistent application data rollback is required. Restore the prior GitHub branch rule through the same authenticated interface if protection must be rolled back.
