# Token-Efficient Coding Workflow

Use this workflow to reduce repeated context and verification output without weakening task-risk controls. OpenAI's current model guidance recommends lean prompts, task-relevant tools, and evaluation on representative workloads: <https://developers.openai.com/api/docs/guides/latest-model>.

## Task brief

Start with exactly these six fields. Derive discoverable facts from the repository instead of asking the owner.

```markdown
Goal:
Scope:
Out of scope:
Constraints:
Acceptance:
Verification:
```

## Context loading

1. Classify the task with `TASK_RISK_CLASSIFICATION.md`.
2. Run `node scripts/task-context.mjs --task <id> --risk <L0-L4> --paths <paths...> [--terms <terms...>]`.
3. Read root and returned scoped rules, returned canonical headings, ADRs, live symbols, call sites, tests, and dependency manifests.
4. Read the full canonical specification only for L3/L4, a change spanning two or more domains, or suspected `SPEC_DRIFT`.
5. Do not read the optimization tracker unless the task belongs to that program or changes project state.

The task-context packet is live, bounded discovery evidence. It never replaces the commit-bound generated inventory or its final freshness gate.

## Artifact policy

| Risk | Before implementation | Completion evidence |
|---|---|---|
| L0 | Task brief | Compact final summary |
| L1 | Task brief; Change Contract only for user-visible behavior, non-trivial rollback, or drift | Compact final summary unless tracked or risk remains |
| L2 | Saved Change Contract | Saved handoff and independent diff review |
| L3 | Approved Change Contract | Saved handoff and independent specialist review |
| L4 | Accepted ADR and approved staged Change Contract | Saved handoff and architecture plus security/data review |

Evidence Packets should link to paths, symbols, headings, and manifests. Do not copy source files or full command output into documentation.

## Coding and verification loop

1. Run the closest baseline check.
2. Edit one coherent behavior boundary.
3. Run its targeted test.
4. Repeat steps 2–3 until stable.
5. Run applicable lint/type/architecture checks.
6. Run the complete affected risk-matrix gate once.
7. Use `node scripts/verify.mjs <mode> --task <id>` for compact output and a full ignored log/manifest.
8. Use `--resume <manifest>` only for an unchanged local source/toolchain fingerprint. CI never resumes; integration, migration, coverage, and E2E are never reusable.

Start a new task only at a clean checkpoint when the phase or scope changes. Keep cross-task handoffs within 40 lines and link the verification manifest.

## Model and reasoning routing

This table guides new tasks and reviewers; it does not attempt to switch a running task's model.

| Workload | Implementation | Review |
|---|---|---|
| L0, inventory, mechanical scan | `gpt-5.6-luna`, low | Self-review |
| L1 normal coding | `gpt-5.6-terra`, medium | Self-review |
| L2 cross-layer or CI | `gpt-5.6-terra`, medium | Independent `gpt-5.6-terra`, medium |
| L3 security, data, or governed AI | `gpt-5.6-sol`, high | Independent specialist `gpt-5.6-sol`, high |
| L4 breaking architecture | `gpt-5.6-sol`, xhigh | Independent specialist `gpt-5.6-sol`, xhigh |

Use `max` only after representative benchmarks show a material quality gain over `xhigh`. Do not create implementation subagents for L0/L1. L2 uses an independent reviewer; L3/L4 use the specialist review required by policy.

## Measurement

Run `node scripts/benchmark-agent-workflow.mjs` against the six fixed scenarios. Record context bytes, packet stdout bytes/lines, elapsed time, source files surfaced, command count, and required gates. The immediate target is at least 40% median context reduction for L0-L2 with no lost gate or test. After ten comparable real tasks, record median tokens when trustworthy telemetry exists; otherwise report proxy metrics and mark actual token reduction unverified.
