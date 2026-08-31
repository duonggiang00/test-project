# Handoff: WORKFLOW-TOKEN-001 — Token-Efficient Coding Workflow

Status: DONE
Risk level: L2

## Outcome

- Summary: Added progressive-disclosure agent guidance, a bounded live task-context packet, compact/redacted verification logs and manifests, conservative local resume support, model routing, and six fixed workflow benchmarks.
- Requirements/task IDs: TOK-001, TOK-002, TOK-003, TOK-004, TOK-005.
- Jest de-duplication: `frontendUnit` now runs the complete Jest project once, while `frontendComponent` is absent from `fast`, `frontend`, and `all`. The targeted `npm run test:component` command remains available for the coding loop.

## Files changed

- `AGENTS.md`, scoped agent rules, and `docs/agent-workflows/` — progressive disclosure, centralized verification matrix, task brief, artifact policy, and model routing.
- `scripts/task-context.mjs` and focused tests — live, bounded, deterministic context discovery with stored-inventory freshness labeling.
- `scripts/verify.mjs` and focused tests — compact/verbose output, ignored full logs, redacted manifest, source/environment/toolchain fingerprints, and safe resume policy.
- `config/agent-workflow-benchmarks.json` and `scripts/benchmark-agent-workflow.mjs` — six representative scenarios and measurable proxy targets.
- `.github/workflows/ci.yml`, `.gitignore`, and generated inventory — failure-log artifact coverage and generated source-state evidence.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `node --test scripts/tests/*.test.mjs` | 0 | 22 | 22 | 0 | 0 | Mapping, budgets, Windows paths, quoting, freshness, explicit truncation, Jest de-duplication, compact dependency failures, broad redaction, and resume tests pass |
| `node scripts/task-context.mjs ...` on stale source | 0 | — | — | — | — | Returned a 2,467-byte/46-line live packet and labeled the stored snapshot stale without writing it |
| `node scripts/task-context.mjs ...` after inventory generation | 0 | — | — | — | — | Labeled the stored snapshot current; output remained within 12 KB/180 lines |
| `node scripts/benchmark-agent-workflow.mjs` | 0 | 6 | 6 | 0 | 0 | Final benchmark values recorded below; actual token telemetry remains unavailable |
| `node scripts/verify.mjs fast --task WORKFLOW-TOKEN-001` | 0 | 534 | 534 | 0 | 0 | 328 backend unit, 24 backend contract, and the complete 182-test frontend Jest project run once; production build passed |
| `node scripts/verify.mjs fast --task ... --resume ...` | 0 | 13 steps | 13 reused | 0 | 0 | Identical source/environment/toolchain fingerprint reused all safe fast steps |
| `node scripts/verify.mjs env --verbose --task ...` | 0 | — | — | — | — | Verbose mode preserved complete child output and wrote the manifest/log |
| `git diff --check` | 0 | — | — | — | — | No whitespace errors |

Canonical integrated compact verification manifest: `reports/agent-workflow/workflow-token-001-integrated-final/fast.json` (ignored local evidence; CI uploads the same report tree on failure).

## Benchmark

| Scenario | Risk | Legacy context bytes | Effective context bytes | Reduction | Packet lines |
|---|---:|---:|---:|---:|---:|
| L0-DOCS | L0 | 82,750 | 1,308 | 98.42% | 40 |
| L1-FRONTEND-COMPONENT | L1 | 29,980 | 6,554 | 78.14% | 95 |
| L1-BACKEND-SERVICE | L1 | 29,822 | 6,050 | 79.71% | 96 |
| L2-BFF-BACKEND | L2 | 39,130 | 22,627 | 42.17% | 102 |
| L2-ROUTING-UI | L2 | 29,980 | 4,458 | 85.13% | 79 |
| L3-AUTH-TENANT | L3 | 47,875 | 21,952 | 54.15% | 96 |

- Acceptance target: median L0-L2 context reduction at least 40%, with every packet at or below 12 KB and 180 lines.
- Verification stdout proxy: the successful fast run's complete child logs plus legacy headings were estimated at 3,643 bytes; compact summaries were 1,836 bytes, a 49.60% reduction, while full logs remained available.
- Actual token reduction: UNVERIFIED until trustworthy Codex task telemetry is available across ten comparable tasks.

## Impact

- API/event/schema contract: None; local CLI interfaces only.
- Migration/data: None.
- Security/ownership/tenant: None. Known sensitive environment values are redacted before logs are persisted, and manifests contain no environment values.
- Dependency/toolchain: No dependency added. Existing Node and uv toolchains are used.

## Manual evidence

- Scenario: Dirty/stale live context lookup.
- Result: The new command succeeded while the existing strict inventory command remained freshness-gated.
- Scenario: Compact failure behavior.
- Result: The initial fast run stopped at missing local database configuration, printed only the command and failure tail, and retained its full log. Creating the same ignored fast environment used by CI resolved the pre-existing environment blocker.
- Scenario: Isolated-worktree frontend dependencies.
- Result: A Windows `node_modules` junction caused ESLint traversal to hang; direct `FRONTEND_NODE_MODULES` resolution completed lint, Jest, and build without changing the original worktree.
- Screenshot/trace: Not applicable; no UI behavior changed.

## Risks and follow-up

- Known risks: The source fingerprint intentionally covers the complete tracked/untracked workspace, so unrelated source edits invalidate all resumable steps. This is conservative and may reuse less work than a future domain-specific fingerprint.
- Unverified items: Actual median token usage and cost across ten comparable real tasks.
- Follow-up tasks: Record real token telemetry only when a trustworthy Codex interface exposes it; do not infer it from byte proxies.
- Independent review: APPROVED with no remaining P1/P2/P3 findings. The first L2 review found incomplete secret-pattern redaction, silent per-category truncation, and incomplete tracker/handoff evidence. All findings were fixed. Final integration additionally corrected the Jest mapping to satisfy the approved no-duplicate requirement and added a regression test; the reviewer confirmed full test collection, safe resume, tracker counts, and `.claude` exclusion.

## Rollback

- Code: Revert the scoped WORKFLOW-TOKEN-001 commit. Existing verification mode names and GitHub required checks remain unchanged.
- Data: Not applicable.
