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

- Verified: `origin` points to `https://github.com/duonggiang00/test-project.git`; the public repository exists and currently has no remote heads.
- Verified: Git is configured to use Git Credential Manager, but no GitHub CLI or token environment variable is available.
- Unresolved: whether Git Credential Manager or an existing browser session can authenticate push, pull-request creation, and branch-protection administration.
