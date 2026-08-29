# AI-008 Baseline and Threshold Approval Packet

Status: NOT READY FOR THRESHOLD APPROVAL

Prepared: 2026-08-29

## Completed prerequisite

AI-007 provides a deterministic evaluator for the owner-approved 40-case
dataset. It reports correctness and groundedness judgments, citation validity,
required-citation coverage, context relevance, injection resistance, latency,
input/output tokens, and estimated cost without persisting raw answers in the
report.

## Evidence still required

Thresholds must not be activated until three full comparable provider
baselines exist. Every run must use:

- dataset SHA-256
  `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`;
- the same provider, model, prompt version, judge version, and scoring schema;
- exactly one observation for all 40 cases;
- explicit correctness/groundedness judgments and injection outcomes;
- provider-reported latency and token telemetry;
- cost from provider telemetry or an owner-approved pricing configuration,
  otherwise explicit null cost coverage.

Synthetic or reference-control observations prove runner determinism only and
must not be used to set provider-quality thresholds.

## Current environment facts

- Provider: `openrouter`.
- Default model: `meta-llama/llama-3.1-8b-instruct`.
- Provider credential: configured; its value was not printed or persisted.
- Approved token pricing: not configured, so cost must remain null unless the
  provider returns authoritative cost telemetry.

## Owner decisions needed after baselines

The approval packet produced from the three reports will show medians, ranges,
worst cases, hard-gate results, telemetry coverage, and proposed regression
tolerances. The owner must then approve:

1. correctness, groundedness, citation, and context-relevance minimums;
2. permitted regression from the accepted baseline;
3. p95 latency and token/cost caps;
4. the 20-case pull-request live subset and the 40-case weekly/manual schedule;
5. the pricing source or the decision to leave cost gating inactive.

Hard structural, complete-coverage, citation, and injection gates do not wait
for quality-threshold approval.
