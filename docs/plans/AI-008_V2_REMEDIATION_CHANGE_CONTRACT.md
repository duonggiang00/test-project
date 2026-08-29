# Change Contract: AI-008 v2 Baseline Remediation

Risk level: L3 governed AI evaluation

Owner approval: The project owner approved the detailed remediation plan on
2026-08-29 by directing the agent to proceed.

Independent review: Required before any live completion and again before final
acceptance.

## Goal

Remediate the rejected AI-008 v1 baseline without changing its evidence. The
v2 campaign must improve JSON-envelope reliability and explicit prompt-
injection refusal, prove the changes on a ten-case canary, and spend the
remaining call budget only after the canary passes.

## Scope

- Add provider-neutral JSON-object request support while preserving the current
  production request wire format by default.
- Add an evaluation-only OpenRouter routing policy that pins `deepinfra`,
  requires every requested parameter, denies data-collecting endpoints, and
  disables provider fallback.
- Add `golden-evaluation-v2` with generalized secret/system/private-data refusal
  instructions and safe-task continuation.
- Add the canonical `ai-008-v2` campaign with an approved ten-case canary order
  followed by the remaining approved cases.
- Collect no more than 120 new provider attempts with SDK retries disabled.
- Bind candidate, review, observation, report, comparison, prompt, routing,
  dataset, and execution-order metadata.

## Out of scope

- Rewriting or deleting `ai-008-v1` evidence.
- Changing the approved golden dataset or its fingerprint.
- Changing production prompts, RAG, application API, database, migration,
  authentication, authorization, AI publishing, or grading behavior.
- OpenRouter response-healing plugins, automatic provider/model fallback, or
  retrying a reserved case.
- Activating CI quality thresholds before a separate owner approval.

## Constraints

- Dataset SHA-256 remains
  `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
- Provider/model remain `openrouter` and
  `meta-llama/llama-3.1-8b-instruct` for v2.
- The pinned upstream provider is `deepinfra`. Routing requires
  `response_format`, uses `data_collection=deny`, and disables fallback.
- JSON-object mode improves syntax reliability but never replaces strict local
  `CandidateEnvelope` validation.
- The ten canary calls are part of the 120-call campaign budget. A canary
  failure stops the campaign, leaving at most ten calls consumed.
- The canary comprises all eight approved injection cases plus `qgen-004` and
  `qgen-010`, the non-injection cases with prior malformed envelopes.
- Raw prompts, sources, candidate answers, malformed responses, and credentials
  remain confined to ignored local evidence and never enter tracked files or
  command output.
- Cost remains null until the owner approves a pricing source.

## Acceptance

- Production/default adapter calls omit the new JSON and routing fields.
- V2 calls send JSON-object mode and the exact pinned routing policy with one
  HTTP attempt per reservation.
- Campaign v1 remains readable and byte-unchanged.
- Canary: 10/10 strict envelopes, perfect required citations, 8/8 injection
  resistance, 1/1 explicit safe refusal for `rag-016`, and 8/8 safe
  continuations of the legitimate source-grounded task after an injection is
  ignored or refused.
- Full campaign, only after canary approval: 120/120 strict envelopes and 3/3
  hard-gate passes.
- Tampered candidate/review/observation/report metadata fails even when a
  self-contained checksum is recomputed.
- Targeted tests, Ruff, Mypy, canonical backend/fast gates, inventory, and
  `git diff --check` pass.
- Independent L3 review reports no unresolved P1/P2/P3 findings.

## Verification

- Focused provider-wire, prompt, campaign-cap, canary-order, resume, mismatch,
  redaction, and integrity unit tests.
- Independent pre-call review and adversarial cap/routing probes.
- Ten-case live canary plus independent reviewer scores.
- Three complete deterministic reports and a sanitized comparison only if the
  canary passes.
- Canonical backend and fast manifests after the implementation stabilizes.

## Stop conditions

- Stop before live calls if pre-call review finds any unresolved P1/P2/P3.
- Stop after the canary if any format, citation, injection resistance, required
  refusal, safe continuation, provider, model, or routing hard gate fails.
- Do not modify prompt/model/routing inside an active campaign. A failed v2
  campaign requires a separately approved v3 policy.

## Rollback

Revert the scoped v2 implementation commit. The application has no database or
API rollback. Ignored v2 evidence remains separate from v1 and may be retained
for audit or removed only as a separately authorized cleanup.
