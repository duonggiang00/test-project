# Change Contract: AI-007 Evaluation and AI-008 Baseline Preparation

Risk level: L3 governed AI evaluation

Owner approval: The project owner instructed implementation of the next work
items on 2026-08-28.

Independent review: Required before AI-007 completion.

## Goal

Implement a deterministic, provider-neutral evaluator for the approved AI-006
dataset and produce the evidence needed for a later owner decision on AI-008
regression thresholds.

## Scope

- Define a strict versioned JSONL observation contract for replayed or live AI
  results.
- Measure correctness, groundedness, citation validity, context relevance,
  prompt-injection resistance, latency, token usage, and estimated cost.
- Emit deterministic aggregate and per-case reports without raw prompts,
  reference context, or provider output.
- Enforce hard structural, citation, and injection gates independently of
  quality threshold policy.
- Add a read-only CLI, focused tests, documentation, repeatability evidence,
  tracker updates, and an independent L3 review.
- Correct the canonical-spec statement that no golden dataset exists.

## Out of scope

- Application API, database, migration, authentication, authorization,
  retrieval, provider/model policy, prompt changes, or product behavior.
- Treating synthetic/reference-control results as provider quality evidence.
- Activating AI-008 quality, latency, token, or cost thresholds before three
  comparable full provider baselines and explicit owner approval.
- Inventing token prices when `AI_TOKEN_PRICING` has no approved entry.

## Constraints

- Evaluation requires the approved AI-006 dataset and matching approval
  manifest.
- Every approved dataset case must have exactly one observation; unknown,
  missing, or duplicate case IDs fail safely.
- Expected-answer cases require an explicit bounded correctness score;
  rubric-based cases require one bounded score for every approved criterion;
  and every case requires an explicit bounded groundedness score. The evaluator
  validates and aggregates supplied judge/reviewer scores but does not claim to
  infer semantic correctness or groundedness from lexical overlap.
- Every injection outcome is explicit. It has no permissive default.
- Reports include output hashes and metrics, never raw candidate answers or
  source content.
- Missing performance telemetry remains explicit null/coverage data and is not
  converted to zero.
- Observation, validation, and report failures must not print raw payloads,
  secrets, or absolute local paths.

## Acceptance

- A complete valid observation set produces deterministic per-case and
  aggregate metrics for all eight required measurement groups.
- JSONL order does not affect observation or report fingerprints.
- Missing/duplicate/unknown observations, invalid rubric scores, secret-like
  output, invalid citations, and successful injection attempts are covered by
  negative tests.
- Citation and injection hard-gate failures produce a report with a failing
  status rather than being hidden by averages.
- Three executions of the same complete replay produce identical metric and
  observation fingerprints.
- Focused tests, Ruff, mypy, canonical backend/fast gates, inventory, and
  `git diff --check` pass.
- Independent L3 review reports no unresolved P1/P2/P3 findings.

## Verification

- Focused evaluator and golden-dataset tests.
- Ruff and mypy for changed evaluator and CLI files.
- Three deterministic full-dataset replay executions.
- Canonical backend gate, including PostgreSQL integration as required by L3.
- Canonical fast gate and independent L3 review.

## Rollback

Revert the scoped evaluator commit. No database or application data rollback is
required because evaluation inputs and reports are file-based and read-only.

## AI-008 approval boundary

AI-008 remains pending until three full provider-result baselines use the same
approved dataset, provider/model/prompt versions, scoring contract, and pricing
policy. The owner must approve the proposed quality and operational thresholds
before they become required CI policy.
