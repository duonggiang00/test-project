# Change Contract: AI-008 v7 Provider-Retry Campaign

Risk level: L3 governed AI evaluation

Owner approval: The active completion objective authorizes a separately
versioned campaign after V6 terminated before receiving a candidate.

Independent review: Required before live calls and final acceptance.

## Goal

Resume AI-008 with a fresh immutable campaign after V6's first reservation
failed with `AI_RATE_LIMIT_EXCEEDED`.

## Scope

- Add `ai-008-v7` and `golden-evaluation-v7`.
- Reuse the byte-identical V6 prompt, model, routing, zero-retry policy,
  five-call replay, ten-call canary, and 40/80/120-call gates.
- Preserve every V1-V6 candidate, report, ledger, and hash unchanged.

## Out of scope

Prompt behavior changes, production behavior, API, database, authentication,
RAG retrieval, dataset, CI thresholds, fallback, retries, response healing,
and application dependencies.

## Acceptance and stop conditions

Use dataset fingerprint
`4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
Require 5/5 replay, the existing ten-case canary, and three passing 40-case
runs. Stop V7 permanently on any provider, format, semantic, or evidence
failure.

## Rollback

Revert the scoped V7 commit. No application or database rollback is required.
