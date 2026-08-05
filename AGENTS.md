# Workspace Agent Policy

This file defines stable workspace-wide behavior. Apply the nearest scoped `AGENTS.md` for implementation details.

## 1. Authority and language

Use this source order when facts conflict:

1. Executable behavior and contracts in current code.
2. Accepted ADRs in `docs/adr/`.
3. `docs/spec/CANONICAL_PROJECT_SPEC.md` and its linked approved contracts.
4. The nearest scoped `AGENTS.md` and applicable workflow.
5. Commit-bound generated inventory.
6. Historical PRDs, plans, memory, and handoffs.

Current code is the operational baseline, not proof that its behavior is correct. Record material conflicts as `SPEC_DRIFT`. Do not change authentication, authorization, migrations, breaking contracts, or major behavior without approval.

Write code, comments, docstrings, technical documentation, UI text, error translations, and engineering handoffs in English.

## 2. Required survey

Before editing:

- Read the canonical specification and relevant accepted ADRs.
- Read the nearest scoped `AGENTS.md`.
- Inspect the actual models, schemas, routes, call sites, components, tests, and configuration involved.
- Check existing dependencies and reusable implementations before adding either.
- Establish the relevant baseline check when the environment supports it.
- Identify pre-existing failures separately from failures caused by the task.

Never guess a field, endpoint, route, permission, or test command. Verify it from live source or executable introspection. Generated inventory is trusted only when its commit metadata matches the current checkout.

## 3. Task risk and approval

Classify work using `docs/agent-workflows/TASK_RISK_CLASSIFICATION.md`.

Prior owner approval is required before implementing:

- Authentication/session lifecycle changes.
- Database migrations or destructive data operations.
- Breaking API or event-contract changes.
- Tenant/ownership isolation changes.
- Major architectural changes or architectural dependencies.

Use subagents only for large or high-risk work. A task has one implementation owner. Security, migration, tenant-isolation, and AI-grading work requires independent review.

## 4. Change contract

For non-trivial work, create a concise change contract before editing. Record scope, current/expected behavior, affected contracts, security/ownership/migration/rollback impact, required verification, assumptions, and unresolved drift.

Use `docs/agent-workflows/CHANGE_CONTRACT.md`. Update the contract when evidence invalidates an assumption.

## 5. Implementation discipline

- Make the smallest coherent change that satisfies the approved scope.
- Preserve unrelated user changes and avoid broad rewrites.
- Keep business logic out of transport/UI layers.
- Reuse an existing implementation only when semantics match.
- Do not add dependencies before checking the existing toolchain.
- Small, common dependencies are allowed only when they do not alter architecture; otherwise request approval.
- Do not weaken tests, delete assertions, or broaden exception handling merely to make checks pass.
- Never report a side effect that was not directly verified.

## 6. Verification

Choose verification by changed behavior and task risk:

1. Run the closest targeted test.
2. Run applicable lint, type, and architecture checks.
3. Run contract/integration tests when crossing process, database, or API boundaries.
4. Run build checks for affected deliverables.
5. Run E2E or visual regression when changing a user flow, routing, auth, hydration, browser behavior, or UI layout.

Do not require full E2E for documentation or isolated pure-logic changes. Do not substitute build/lint for behavioral tests.

Read stdout and stderr, not only the exit code. If a required check cannot run, report the exact blocker and leave the task `BLOCKED` or `REVIEW`, not `DONE`.

## 7. Completion evidence

Use `docs/agent-workflows/HANDOFF.md`. A completed implementation reports task/requirement IDs, files changed, commands and results, test counts, contract/migration/security impact, manual verification, UI evidence, known risks, unverified items, and rollback instructions.

Update `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` when completing a task from that program. Update project state only when a capability, contract, accepted decision, active transition, or blocker changes. Do not manually maintain technical inventories that can be generated from code.

## 8. Safety and repository hygiene

- Use `.env.example` placeholders; never expose or commit secrets.
- Use isolated local/test data for tests and migrations.
- Do not run migrations or destructive operations against shared environments without explicit authorization.
- Validate exact paths before recursive delete or move operations.
- Keep commits scoped and do not stage unrelated changes.
- Agents may create branches, commits, and pull requests when requested or when part of an approved task.

## 9. Canonical references

- Specification: `docs/spec/CANONICAL_PROJECT_SPEC.md`
- Permissions: `docs/spec/PERMISSION_AND_OWNERSHIP_MATRIX.md`
- Error/audit contracts: `docs/spec/ERROR_AND_AUDIT_CONTRACTS.md`
- Architecture decisions: `docs/adr/`
- Optimization tracker: `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md`
