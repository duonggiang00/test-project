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

Before editing, classify the task risk and load only the context needed for that scope:

1. Read this file and the nearest scoped `AGENTS.md`.
2. Run `node scripts/task-context.mjs --task <id> --risk <L0-L4> --paths <paths...>` when available, then read the listed specification sections and ADRs.
3. Read the complete canonical specification only for L3/L4 work, a cross-domain change, or a suspected `SPEC_DRIFT`.
4. Inspect the live models, schemas, routes, call sites, components, tests, configuration, dependencies, and reusable implementations involved.
5. Establish the closest baseline and separate pre-existing failures from task-caused failures.

Do not load the optimization tracker by default. Read it only for a task in that program or when project capability, transition, or blocker state changes.

Never guess a field, endpoint, route, permission, or test command. Verify it from live source or executable introspection. Generated inventory is trusted only when its generator version and relevant source-tree hash match the current checkout; its source commit records the generation base and may precede documentation-only commits.

## 3. Task risk and approval

Classify work using `docs/agent-workflows/TASK_RISK_CLASSIFICATION.md`.

Prior owner approval is required before implementing:

- Authentication/session lifecycle changes.
- Database migrations or destructive data operations.
- Breaking API or event-contract changes.
- Tenant/ownership isolation changes.
- Major architectural changes or architectural dependencies.

Use subagents only for large or high-risk work. A task has one implementation owner. Security, migration, tenant-isolation, and AI-grading work requires independent review.

## 4. Task brief and change contract

Use the six-field task brief and artifact policy in `docs/agent-workflows/TOKEN_EFFICIENT_CODING.md`. L2-L4 work requires a saved Change Contract before editing. L1 work requires one only for user-visible behavior, non-trivial rollback, or unresolved drift. Update the contract when evidence invalidates an assumption.

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

Use the centralized matrix in `docs/agent-workflows/TASK_RISK_CLASSIFICATION.md`: targeted behavior first, applicable static checks next, and the complete affected gate once after the implementation stabilizes. Do not substitute build/lint for behavioral tests or require full E2E for documentation and isolated pure logic.

Read stdout and stderr, not only the exit code. If a required check cannot run, report the exact blocker and leave the task `BLOCKED` or `REVIEW`, not `DONE`.

## 7. Completion evidence

Use the artifact policy in `docs/agent-workflows/TOKEN_EFFICIENT_CODING.md`. Persist a detailed `docs/agent-workflows/HANDOFF.md` record for L2-L4 work, tracked-program tasks, or unresolved risk; use a compact final summary for ordinary L0/L1 work. Reference verification manifests instead of copying full logs.

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
- Token-efficient workflow: `docs/agent-workflows/TOKEN_EFFICIENT_CODING.md`
