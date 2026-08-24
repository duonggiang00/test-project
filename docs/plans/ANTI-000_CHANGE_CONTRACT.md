# Change Contract: ANTI-000 Stabilize the remediation baseline

Risk level: L2
Owner: Primary implementation agent
Approval required: No additional approval
Approval evidence: The owner approved the staged remediation plan and selected "finalize current changes" as the worktree strategy on 2026-08-24.

## Scope

- In scope: map every current tracked and untracked change to an existing task, verify the closest applicable checks, complete missing handoff evidence, and create scoped commits until the worktree is clean.
- Out of scope: change the behavior of an existing task, discard or rewrite user changes, start SEC-003 through SEC-007, or regenerate contracts merely to hide an unexplained diff.

## Behavior

- Before: more than one hundred working-tree entries from several completed or review-stage tasks overlap backend, frontend, tests, generated artifacts, and documentation.
- After: every retained change is owned by a task contract and handoff, committed in a reviewable checkpoint, and the clean checkout has a reproducible verification baseline.
- Preserved invariants: no user change is dropped; task assertions are not weakened; current code and accepted ADRs remain authoritative.

## Expected files and contracts

- Files/modules: existing task changes, their change contracts and handoffs, generated OpenAPI/inventory only when the owning executable contract changed.
- API/event/schema impact: none introduced by ANTI-000; any existing impact remains attributed to its original task.
- Migration/data impact: none introduced; no migration is executed against shared data.
- Security/ownership/tenant impact: none introduced; security-relevant existing changes must retain their original review status.

## Verification contract

- Targeted tests: use the commands recorded by each mapped task and rerun any missing or stale targeted check.
- Static/type checks: architecture guard plus affected lint/type checks.
- Integration/PostgreSQL checks: required only for mapped tasks that changed database, query, authorization, grading, or concurrency behavior.
- Build/E2E/visual checks: required for mapped frontend route, hydration, interaction, or snapshot changes.
- Manual verification: inspect the final scoped diffs and confirm `git status --short` is empty after commits.

## Rollback

- Code rollback: revert the individual task commit; do not reset or overwrite unrelated commits.
- Data rollback: not applicable because this checkpoint performs no shared-data mutation.

## Assumptions and drift

- Verified assumptions: the checkout has one Alembic head, `b6d4f0a17c53`; existing task contracts and handoffs cover most uncommitted changes.
- Unresolved assumptions: individual changes remain unowned until the mapping audit proves their task association.
- SPEC_DRIFT: authentication, design-system, and other remediation drift remains intentionally deferred to later approved checkpoints.
