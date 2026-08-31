# Handoff: AI-008 V8 Accepted Baseline

Status: REVIEW

Risk level: L3 governed AI evaluation

## Outcome

- Added the evaluation-only `ai-008-v8` campaign using
  `openai/gpt-4.1-mini` through OpenRouter with OpenAI-only routing, zero
  retries, no fallback, denied data collection, and strict JSON handling.
- Preserved the production model/prompt and immutable V1-V7 evidence.
- Passed the five-case replay and ten-case canary before completing three
  independently reviewed 40-case runs.
- Achieved 120/120 valid envelopes, 3/3 hard-gate runs, 24/24 safe
  continuations, and 3/3 required refusals.
- Prepared the owner threshold packet. No GitHub Actions threshold is enabled.

## Files changed

- `backend/app/ai/evaluation/` — allowlisted V8 campaign, routing, canary, and
  comparison bindings.
- `backend/scripts/` — V8-aware governed evaluation CLIs.
- `backend/tests/unit/test_ai_live_baseline.py` — exact wire policy and V8 gate
  coverage.
- `docs/plans/AI-008_V8_CHANGE_CONTRACT.md` — approved scope and stop rules.
- `docs/plans/AI-008_BASELINE_AND_THRESHOLD_PACKET.md` — owner decision packet.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — current task state.

## Live evidence

| Evidence | Result |
|---|---|
| Failure replay | 5/5 format, citation, injection, and continuation; 1/1 refusal |
| Full canary | 10/10 format/citations; 8/8 injection and continuation; 1/1 refusal |
| `baseline-001` | 40/40 valid; all hard gates pass; correctness 0.843750; groundedness 0.956250 |
| `baseline-002` | 40/40 valid; all hard gates pass; correctness 0.828125; groundedness 0.950000 |
| `baseline-003` | 40/40 valid; all hard gates pass; correctness 0.812500; groundedness 0.937500 |
| Comparison | 120/120 valid; 3/3 hard-gate runs; acceptance ready |

Sanitized evidence is under the ignored path
`backend/reports/ai-evaluation/ai-008-v8/`. The comparison binds each report,
observation set, dataset, case order, routing policy, campaign, prompt, model,
and judge version. Raw answers are not copied into tracked artifacts.

## Verification

Pre-call verification passed 64 focused tests, Ruff, mypy, the architecture
guard (`current=0`, `baseline=0`, one waiver), inventory generation, and the
13-step fast gate.

The final review identified that continuation/refusal judgments were not yet
bound into comparison acceptance. The finding was remediated by extending the
strict review schema, hashing each complete run review, requiring exact
judgment scope, and including 3/3 semantic run gates in final acceptance.

| Command | Result |
|---|---|
| Focused comparison/review/live tests | 58/58 passed |
| Focused Ruff and mypy | Passed |
| `node scripts/verify.mjs backend --compact --task ai-008-v8-final-backend` | 5/5 passed; 459 unit, 24 contract, 171 PostgreSQL integration; manifest `reports/agent-workflow/ai-008-v8-final-backend/backend.json` |
| `node scripts/verify.mjs fast --compact --task ai-008-v8-final-fast2` | 13/13 passed; 459 backend unit, 24 contract, 182 frontend unit, production build; manifest `reports/agent-workflow/ai-008-v8-final-fast2/fast.json` |
| `node scripts/project-inventory.mjs generate` | Generated source fingerprint `b1f6f3752690cbe7147ca97cc4660024a6b777251a911208b4ebdb5113d95b3d` |
| V8 comparison regeneration | 120/120 format, 3/3 existing hard-gate runs, 3/3 semantic-gate runs, acceptance ready |

The original derived comparison was preserved as
`comparison.pre-semantic-gates.json` with SHA-256
`b6105ca372f6fb964103d66efe2b9b5dccf065e0696499c00a3cf57f0ce4079f`.
The authoritative comparison is `comparison.json`; its three semantic review
hashes bind the independently supplied continuation/refusal judgments.

Final independent L3 re-review approved the remediation with no remaining
P1/P2/P3 findings. It confirmed complete manifests, legacy serialization,
secret safety, threshold arithmetic, and unchanged CI/production boundaries.

## Impact

- API/event/schema contract: unchanged.
- Migration/data: unchanged; evaluation artifacts are ignored local files.
- Security/ownership/tenant: unchanged.
- Production provider/model/prompt: unchanged.
- CI: unchanged pending explicit owner threshold approval.

## Risks and follow-up

- Semantic scores depend on the independent review contract.
- Cost remains null and cannot gate until a pricing source is approved.
- The live CI implementation must protect provider secrets from fork pull
  requests and prove a deterministic 20-case subset before activation.
- RAG-SEMANTIC-001 needs a separate retrieval-quality evaluation; this baseline
  does not validate production retrieval.

## Rollback

Revert the scoped V8 commits. No database or application-data rollback is
required.
