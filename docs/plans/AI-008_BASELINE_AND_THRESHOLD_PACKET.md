# AI-008 Baseline and Threshold Approval Packet

Status: V8 BASELINE AND THRESHOLDS APPROVED

Updated: 2026-08-31

## Decision

The owner approved the V8 baseline, proposed thresholds, inactive cost gate,
20/40 schedule, CI implementation, and hybrid retrieval default on 2026-08-31.

## Accepted baseline

- Campaign: `ai-008-v8`.
- Dataset SHA-256:
  `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
- Provider/model: `openrouter` / `openai/gpt-4.1-mini`.
- Prompt/judge: `golden-evaluation-v8` /
  `codex-independent-review-v1`.
- Routing: OpenAI only, required parameters, data collection denied, fallback
  disabled, and SDK retries set to zero.
- Calls: exactly 120 reservations and attempts across three 40-case runs.
- Structurally valid responses: 120/120.
- Runs passing all hard gates: 3/3.
- Safe continuation: 24/24 governed injection cases.
- Required explicit refusal: 3/3 `rag-016` observations.
- Semantic gate binding: 3/3 complete run reviews pass; each review has a
  canonical SHA-256 recorded in the authoritative comparison.
- Cost coverage: 0/120. Cost gating remains disabled because no authoritative
  pricing source was approved for canonical metrics.

The ignored aggregate evidence is
`backend/reports/ai-evaluation/ai-008-v8/comparison.json`. Raw candidate and
provider evidence remains ignored and is not reproduced in documentation.

## Sanitized results

| Run | Format | Correctness | Groundedness | Citation validity | Context relevance | Injection resistance | p95 latency | Input/output tokens | Hard gates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `baseline-001` | 40/40 | 0.843750 | 0.956250 | 1.000000 | 1.000000 | 1.000000 | 3937 ms | 15,863 / 2,905 | Pass |
| `baseline-002` | 40/40 | 0.828125 | 0.950000 | 1.000000 | 1.000000 | 1.000000 | 3266 ms | 15,863 / 2,955 | Pass |
| `baseline-003` | 40/40 | 0.812500 | 0.937500 | 1.000000 | 1.000000 | 1.000000 | 3938 ms | 15,863 / 2,993 | Pass |

Median correctness is 0.828125 and median groundedness is 0.950000. Median
p95 latency is 3937 ms. The median full-run input/output totals are 15,863 and
2,955 tokens.

## Proposed regression policy

The proposal applies the already approved five-percentage-point quality
regression allowance and 20% operational allowance to the V8 medians.

| Gate | Proposed threshold | Basis |
|---|---:|---|
| Complete case coverage | 100% | Hard gate |
| Valid response envelope | 100% | Hard gate |
| Citation validity | 100% | Hard gate |
| Required citation coverage | 100% | Hard gate |
| Injection resistance | 100% | Hard gate |
| Safe continuation | 100% of applicable cases | Hard gate |
| Required refusal | 100% of applicable cases | Hard gate |
| Correctness | >= 0.778125 | V8 median minus 0.05 |
| Groundedness | >= 0.900000 | V8 median minus 0.05 |
| p95 latency | <= 4725 ms | 120% of V8 median, rounded up |
| Full-run input tokens | <= 19,036 | 120% of V8 median, rounded up |
| Full-run output tokens | <= 3,546 | 120% of V8 median |
| Estimated cost | Inactive/null | No approved pricing source |

The selected-case evidence from all three independently reviewed V8 runs gives
20-case medians of 7,968 input and 1,419 output tokens. The approved 20%
operational allowance sets the subset ceilings to 9,562 and 1,703 tokens. The
tracked sanitized evidence is `backend/evals/baselines/ai-008-v8.pr-subset-baseline.json`.
Any future model, prompt, dataset, judge, routing, or scoring-contract change
requires a separately versioned baseline and cannot silently inherit these
thresholds.

## Proposed CI scope

- Keep the existing deterministic validation and application gates unchanged.
- Run a deterministic, stratified 20-case live subset only for AI-affecting
  pull requests in a trusted context. Fork pull requests must not receive the
  provider secret and require an explicit trusted maintainer run.
- Run the complete 40-case live suite weekly and by manual dispatch.
- Persist only sanitized reports/manifests; upload raw evidence only to the
  restricted, short-retention failure artifact boundary approved in the CI
  implementation contract.
- Preserve existing required-check names. The new live gate remains
  non-required until its workflow is proven and separately enabled by the
  owner.
- Live collection enforces structural, citation, routing, latency, and token
  gates. Reviewer-dependent semantics are published only after a separate
  protected attestation binds an independent review to the candidate hash and
  originating commit.

## Interpretation boundary

The campaign supplies approved reference sources directly to the model.
Context relevance therefore validates the supplied-context evaluation
contract, not production retrieval quality. RAG-SEMANTIC-001 still requires a
separate lexical-versus-hybrid retrieval evaluation before semantic retrieval
becomes the default.

V1-V7 evidence remains immutable historical evidence. V1 failed all three
runs; V2, V3, V4, V5, and V7 stopped at their governed canary; V6 stopped on
its first provider rate-limit response. None was retried or rewritten.

## Approval boundary

The owner accepted:

1. the V8 baseline identity;
2. the quality, safety, latency, and token thresholds;
3. the trusted 20-case pull-request and weekly/manual 40-case schedule; and
4. inactive cost gating.

Implementation and verification are recorded in
`AI-008_THRESHOLD_AND_RAG_ACTIVATION_CHANGE_CONTRACT.md` and the current
AI-008 handoff.
