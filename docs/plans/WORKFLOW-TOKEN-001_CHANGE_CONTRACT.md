# Change Contract: WORKFLOW-TOKEN-001 — Token-Efficient Coding Workflow

Risk level: L2
Owner: Primary coding agent
Approval required: Yes, because the task changes shared verification tooling
Approval evidence: The project owner explicitly requested implementation of the approved WORKFLOW-TOKEN-001 plan on 2026-08-26.

## Scope

- In scope:
  - Replace broad default reading with risk-based, progressive-disclosure workflow guidance.
  - Add a bounded, read-only live task-context command.
  - Add compact verification output, full ignored logs, a redacted manifest, and safe local resume support.
  - Add model/reasoning routing guidance and six fixed workflow benchmark scenarios.
  - Update the optimization tracker and create an evidence-backed handoff.
- Out of scope:
  - Application behavior, APIs, database schema, migrations, authentication, authorization, tenant isolation, or AI runtime behavior.
  - Renaming or removing GitHub required checks.
  - Caching integration, migration, coverage, or E2E results.
  - Fabricating token measurements when Codex usage telemetry is unavailable.

## Behavior

- Before:
  - The root policy directs agents to read the complete canonical specification before every edit.
  - `project-inventory.mjs context` rejects a stale stored inventory and can emit unbounded JSON.
  - `verify.mjs` streams complete child-process output and produces no task-level verification manifest.
- After:
  - Agents load only task-relevant specification sections and ADRs unless L3/L4, cross-domain, or SPEC_DRIFT conditions require a full read.
  - `task-context.mjs` builds a bounded packet from live source without rewriting the stored inventory and labels stored inventory freshness explicitly.
  - Verification defaults to compact summaries while preserving complete ignored logs and machine-readable evidence.
  - Canonical frontend verification runs the complete Jest project once; the separate component command remains available only for targeted coding-loop use.
- Preserved invariants:
  - Canonical source authority, approval boundaries, risk-based review, test strength, and GitHub required-check names remain unchanged.
  - Stored generated inventory remains commit-bound and is still required to pass the canonical inventory gate.
  - Frontend acceptance coverage and test count are preserved: the full Jest project collects all source and component suites in one required step.

## Expected files and contracts

- Files/modules:
  - Root/scoped agent workflow documentation and the risk matrix.
  - `scripts/task-context.mjs`, `scripts/project-inventory.mjs`, and focused Node tests.
  - `scripts/verify.mjs`, CI diagnostic artifact paths, benchmark configuration/results, tracker, and handoff.
- API/event/schema impact: None. New and extended local CLI interfaces only.
- Migration/data impact: None.
- Security/ownership/tenant impact: None. Logs and manifests must not contain environment values or secrets.

## Verification contract

- Targeted tests:
  - Node tests for path-to-context mapping, bounded output, stale inventory handling, Windows paths, compact output, failure tails, manifests, redaction, and resume invalidation.
  - Six deterministic workflow benchmark scenarios.
- Static/type checks:
  - Syntax checks for changed Node scripts, architecture guard, inventory check, and `git diff --check`.
- Integration/PostgreSQL checks:
  - Not required by changed behavior. The canonical fast gate may initialize backend introspection but must not connect to PostgreSQL.
- Build/E2E/visual checks:
  - Canonical fast gate. No E2E or visual change is in scope.
- Manual verification:
  - Run task-context against frontend, backend, BFF, routing, auth, and documentation examples.
  - Inspect compact and verbose outputs and verify complete logs remain available.
  - Obtain independent L2 diff review.

## Rollback

- Code rollback: Revert the scoped WORKFLOW-TOKEN-001 commit(s). Existing verification modes and stored inventory remain compatible.
- Data rollback: Not applicable.

## Assumptions and drift

- Verified assumptions:
  - The implementation is isolated in `codex/workflow-token-001` at commit `5b1a8fc`, separate from the dirty `frontend/english-coverage-001` worktree.
  - Reports under backend/frontend report directories are ignored by Git.
  - Official OpenAI guidance supports lean prompts, representative-task evaluation, and the planned Luna/Terra/Sol routing.
- Unresolved assumptions:
  - Actual per-task Codex token telemetry may not be programmatically available; proxy metrics remain authoritative until it is available.
- SPEC_DRIFT:
  - None found.
