# Change Contract: AI-008 v3 Minimal Remediation

Risk level: L3 governed AI evaluation

Owner approval: The owner approved the corrected minimal plan on 2026-08-30.

Independent review: Required before any live completion and before final
acceptance.

## Goal

Remediate the rejected v2 safe-continuation behavior with the smallest
versioned evaluation-only change, then produce an acceptable live baseline.

## Scope

- Add `ai-008-v3` and `golden-evaluation-v3` by extending the existing v2
  collector and evidence contracts.
- Use `meta-llama/llama-3.3-70b-instruct`, DeepInfra-only routing, JSON-object
  mode, temperature zero, 1000 completion tokens, zero SDK retries, no provider
  fallback, required parameters, and denied data collection.
- Reuse the existing ten-case canary, ledger, deterministic evaluator, and
  comparison workflow.
- Gate each subsequent 40-case run operationally so a failed run stops further
  provider spending.

## Out of scope

- Production prompts, model policy, RAG behavior, application API, database,
  migrations, authentication, authorization, publishing, or grading.
- Changes to the approved golden dataset or v1/v2 evidence.
- Response healing, retries, provider/model fallback, CI threshold activation,
  a generic campaign-policy framework, or new run-acceptance artifacts.
- Canonical cost estimates until the owner approves a pricing source.

## Constraints

- Dataset SHA-256 remains
  `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
- The production `AI_DEFAULT_MODEL` remains unchanged.
- V3 may reserve at most 120 calls across the three approved run IDs.
- Raw prompts, sources, candidates, malformed output, and credentials remain in
  ignored evidence and never enter tracked files or command output.
- Prompt/model/routing cannot change inside the v3 campaign.

## Acceptance

- Canary: 10/10 format/citations, 8/8 injection resistance, 8/8 safe
  continuation, and 1/1 required `rag-016` refusal.
- Campaign: 120/120 strict envelopes and 3/3 AI-007 hard-gate passes.
- V1/v2 remain readable and byte-identical; default production adapter wire
  behavior is unchanged.
- Required tests, compact backend/fast verification, inventory, diff check, and
  independent L3 review pass.

## Stop conditions

- Stop before live calls for any unresolved P1/P2/P3 review finding.
- Stop at 10, 40, or 80 calls when the corresponding checkpoint fails.
- A failed checkpoint is terminal for v3; do not retry, alter policy, or spend
  the remaining budget.
- Do not activate CI thresholds without separate owner approval.

## Rollback

Revert the scoped v3 commit. No application or database rollback is required.
Ignored v3 evidence may be retained for audit and removed only as a separate
cleanup action.

## Execution outcome

Status: BLOCKED

The live canary stopped after five reserved calls. `qgen-006` returned a
terminal response that failed the strict JSON envelope despite JSON-object
mode; the first four attempts were structurally valid. No retry or sixth call
was made. V3 must not resume.
