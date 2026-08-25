# Change Contract: CI-GITHUB-001 — First GitHub Execution and Branch Protection

Risk level: L2 repository-governance change
Owner: Primary coding agent
Approval required: Yes
Approval evidence: The project owner requested execution of the remaining CI/GitHub work on 2026-08-25.

## Scope

- Commit the already reviewed workflow-tracker reconciliation without staging unrelated local files.
- Push the existing `main` history to the configured public `origin`.
- Observe the first push-triggered `Fast verification`, `PostgreSQL integration`, and `Real backend smoke E2E` jobs.
- Create a narrowly scoped pull request to exercise `Fast verification`, `Coverage regression`, and `Mocked browser matrix` when authentication permits.
- Apply the machine-readable `config/github-branch-policy.json` policy only after the required check contexts exist.
- Capture GitHub-hosted results and update the canonical tracker/handoff.

Out of scope:

- Application, API, database-schema, authentication, authorization, or dependency changes.
- Weakening checks, assertions, timeouts, or required-check policy to obtain a passing run.
- Force-pushing, deleting remote branches with unmerged work, or changing repository visibility.

## External impact

- The first push publishes the repository's committed history to the configured public GitHub repository.
- Branch protection will require `Fast verification`, `Coverage regression`, and `Mocked browser matrix`, require the branch to be current, block force pushes, and block branch deletion.
- Workflow permissions remain `contents: read`; no repository secrets are added or printed.

## Verification contract

- Before push: scoped staged diff, `git diff --cached --check`, branch-policy checker, and canonical fast verification through the pre-commit hook.
- Push workflow: inspect every job conclusion and relevant stdout/stderr, not only the overall run status.
- Pull-request workflow: inspect all three required PR check conclusions and the flaky-test ownership policy output.
- Protection: read back the repository rule and verify exact required contexts, strict/up-to-date behavior, force-push denial, and deletion denial.
- Negative proof: demonstrate that an unverified pull request cannot merge without bypassing or weakening policy.

## Rollback

- Documentation commit: revert with a new commit; do not rewrite published history.
- Pull-request probe: close it after evidence is captured if no product change is intended.
- Branch protection: restore the previous repository rule through the same authenticated GitHub interface and record the read-back result.
- A failed workflow remains visible as evidence; fix the cause in a new commit rather than deleting or rewriting the run.

## Assumptions and blockers

- Verified: `origin` points to `https://github.com/duonggiang00/test-project.git`; the public repository exists and `main` now tracks `origin/main`.
- Verified: Git Credential Manager authenticates workflow-bearing pushes after browser reauthorization; no GitHub CLI or token environment variable is available.
- Unresolved: whether the connected GitHub API client has repository-administration permission for branch protection.

## Execution evidence

- Git Credential Manager authentication was refreshed after GitHub rejected the first push because the previous OAuth credential lacked `workflow` scope; retrying then published `main` successfully without exposing a token.
- Push run `32825477755` failed before checkout in `Fast verification`; the official job log reports `Unable to resolve action astral-sh/setup-uv@v8`.
- The GitHub releases API on 2026-08-25 reports current releases for `actions/checkout@v7`, `actions/setup-node@v7`, `astral-sh/setup-uv@v10.0.1`, and `actions/upload-artifact@v7`. Git ref checks confirm every selected ref exists; setup-uv has no moving `v10` tag, so its exact release tag is pinned before rerunning hosted verification.
- Push run `32826565120` resolved and installed every action, then exposed cross-environment inventory drift. Inspection found that raw text-byte hashing was line-ending-sensitive; generator `1.0.1` canonicalizes CRLF only for text-like buffers, preserves binary bytes, and enforces both invariants with built-in fixtures.
- A source-set comparison then found the decisive drift: the local generator included two ignored Playwright authentication-state files under `frontend/tests/e2e/playwright/.auth`, while a clean GitHub checkout did not. The generator now excludes `.auth` runtime state; its relevant tracked/source count is 399 on both environments.
- Push run `32827872723` passed inventory, architecture, OpenAPI, lint, and type checks, then failed two configuration unit tests because a workflow-global `DATABASE_URL` overrode their isolated settings. The variable is now scoped only to the PostgreSQL integration, coverage, and real-E2E jobs; fast and mocked jobs remain database-independent.
- Push run `32828489067` then showed that model/inventory introspection itself requires settings initialization before unit tests. Both static introspection subprocesses now receive a non-connecting placeholder URL only when no real URL exists; the parent fast process and pytest environment remain unmodified.
- Push run `32829081721` passed model drift and inventory, then identified the remaining application-importing static subprocess: the OpenAPI emitter. It now uses the same isolated non-connecting fallback; a source scan confirms no other fast-gate emitter imports `app.main`.
- Push run `32829696817` passed every static gate, then showed that pytest's root `conftest` imports the application before configuration-isolation tests execute. The Fast job now copies the tracked placeholder-only `.env.example` to the ignored `.env`; default app imports can initialize without placing `DATABASE_URL` in the process environment, so `_env_file=None` tests remain isolated.
