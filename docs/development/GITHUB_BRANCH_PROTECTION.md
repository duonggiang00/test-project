# GitHub Branch Protection Policy

Status: defined locally; remote application and observed check contexts are pending.

The machine-readable source is `config/github-branch-policy.json`. Run
`node scripts/check-github-branch-policy.mjs` to confirm that the workflow and
policy still agree.

## Required pull-request gates

Protect `main`, require the branch to be up to date, and select the observed
GitHub check contexts corresponding to these workflow jobs:

| Job ID | Stable job name | Purpose |
|---|---|---|
| `fast` | `Fast verification` | Environment, drift, architecture, contracts, lint, unit/component tests, and build |
| `coverage-pr` | `Coverage regression` | PostgreSQL-backed coverage baseline and 80% changed-code policy |
| `mocked-e2e` | `Mocked browser matrix` | Backend-independent Chromium, Firefox, WebKit, and mobile critical flow |

Do not configure a required context by guessing its GitHub-rendered label.
Select it from the first successful pull-request run, then record the observed
context if GitHub renders a value different from the stable job name above.

## Post-merge checks

`PostgreSQL integration` and `Real backend smoke E2E` run only on pushes to
`main`. They are post-merge health checks under the current approved workflow,
so they must not be configured as pull-request requirements. Moving either
check before merge changes CI scope and must update the workflow, policy, time
budget, and tracker together.

## Application checklist

Application remains pending until a GitHub remote exists:

1. Push `main` and open a pull request that changes a harmless tracked file.
2. Confirm all three required pull-request jobs execute and capture their exact
   GitHub check-context labels.
3. Configure a branch ruleset or branch protection for `main` with the three
   observed required contexts, strict/up-to-date branches, force-push blocking,
   and branch-deletion blocking.
4. Prove a failing required check blocks merge.
5. Prove all green required checks allow the expected merge path.
6. Record the repository/ruleset link and evidence in CI-010 before moving it
   from `REVIEW` to `DONE`.

Repository settings are external mutations. Do not apply or weaken protection
silently, and do not mark CI-010 complete from local workflow parsing alone.
