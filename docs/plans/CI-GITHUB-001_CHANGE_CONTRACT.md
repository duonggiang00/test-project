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
- Push run `32826565120` resolved and installed every action, then exposed a cross-platform inventory defect: Windows-generated CRLF bytes did not match the LF checkout on Ubuntu. Generator `1.0.1` canonicalizes CRLF only for text-like buffers, preserves binary bytes, and enforces both invariants with built-in fixtures.
