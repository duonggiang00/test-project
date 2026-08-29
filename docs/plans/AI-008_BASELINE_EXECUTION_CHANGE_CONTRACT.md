# Change Contract: AI-008 Live Baseline Execution

Risk level: L3 governed AI evaluation

Owner approval: The project owner approved proceeding on 2026-08-29 after
being told that the run would use at most 120 OpenRouter candidate calls with
the configured default model.

Independent review: Required before baseline evidence is accepted.

## Goal

Collect three comparable full-provider baselines for the approved 40-case
golden dataset and prepare a compact threshold approval packet without enabling
regression policy prematurely.

## Scope

- Add a strict, capped, resumable collector that calls the existing provider
  abstraction once per case.
- Use one versioned evaluation prompt contract for all three runs and the same
  configured provider/model.
- Store candidate outputs only under the ignored
  `backend/reports/ai-evaluation/` path.
- Preserve provider latency and token telemetry. Keep cost null because no
  owner-approved pricing configuration exists.
- Produce complete AI-007 observation/report files through a declared
  reviewer-scoring step.
- Compare three reports and prepare thresholds for explicit owner approval only
  if every structural and safety hard gate passes.

## Out of scope

- More than 120 provider candidate calls.
- Automatic provider/model fallback, retrying a completed case, or changing
  production provider/model policy.
- Enabling quality, latency, token, or cost thresholds in CI before the owner
  approves the exact proposal.
- Application API, database, migration, authentication, authorization,
  retrieval, production prompts, or product behavior changes.

## Constraints

- Dataset SHA-256 must remain
  `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
- Every baseline uses `openrouter` and the configured
  `meta-llama/llama-3.1-8b-instruct` model unless the run fails safely and the
  owner separately approves a replacement.
- The collector prompt is `golden-evaluation-v1`. It measures the declared
  evaluation workload and must not be represented as an unchanged production
  prompt path.
- A persisted attempt is never called again during resume. A malformed response
  consumes its reservation, remains a visible terminal structural failure, and
  stops that invocation; an explicit later resume may continue only unattempted
  cases. Re-running a fully attempted baseline is an idempotent no-call summary.
  The command
  rejects a changed dataset, provider, model, prompt version, run identifier,
  or campaign binding.
- The campaign has exactly three approved run IDs and one canonical ignored
  ledger/output directory. CLI callers cannot override provider, model,
  temperature, output-token cap, artifact path, or retry policy. Baseline calls
  disable SDK retries, so one reservation means at most one HTTP request.
- Provider errors are sanitized. Raw prompts, context, candidate answers, and
  credentials are not printed or committed.
- Candidate citation IDs come from a strict response envelope. Correctness,
  groundedness, and injection outcomes come from the declared reviewer process,
  not candidate self-assessment or lexical similarity.
- All approved case sources are supplied directly to the evaluation prompt, so
  context-relevance coverage in this campaign describes the supplied context
  only. It is not evidence for production retrieval quality and cannot set a
  production retrieval threshold.
- Cost remains null unless authoritative provider telemetry is available; no
  local price is invented.

## Acceptance

- Collector tests cover deterministic prompt construction, strict envelope
  parsing, cap enforcement, resume without duplicate calls, mismatch refusal,
  sanitized provider failures, and atomic persistence.
- Three runs each contain exactly one terminal candidate record for all 40
  approved cases and use identical dataset/provider/model/prompt metadata.
  Threshold acceptance additionally requires 120/120 structurally valid
  responses and 3/3 hard-gate passes.
- Reviewer-scored observations pass the AI-007 structural contract; hard-gate
  failures remain visible rather than being replaced by averages.
- The comparison packet reports medians, ranges, worst cases, hard gates, and
  telemetry coverage while excluding raw prompts/context/answers.
- Targeted tests, Ruff, mypy, canonical backend/fast gates, inventory, and
  `git diff --check` pass.
- Independent L3 review reports no unresolved P1/P2/P3 finding.

## Verification

- Focused baseline collector, evaluator, and dataset tests.
- One first-case live call followed by resume proves the cap and persistence
  path before completing the remaining approved calls.
- Three complete baseline files and three deterministic evaluation reports.
- Canonical backend and fast gates plus independent L3 review.

## Rollback

Revert the scoped collector/comparison commit and remove ignored local baseline
artifacts if desired. No database or application data rollback is required.

## Approval boundary after collection

Baseline collection does not authorize threshold enforcement. The owner must
approve the exact metric minimums, regression tolerance, latency/token caps,
live subset/schedule, and null-cost policy before AI-008 can change CI.

## Execution result

The approved budget is exhausted at exactly 120 calls. The campaign produced
115/120 structurally valid responses and 0/3 hard-gate passes because every run
contained one independently judged injection failure. Runs 001 and 002 also
failed citation validity. Consequently, no statistical threshold proposal or
CI enforcement was produced. A new campaign/prompt version and any additional
provider-call budget require separate owner approval; this failed campaign must
remain unchanged as evidence.
