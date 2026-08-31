# Change Contract: AI-008 v8 Instruction-Following Campaign

Risk level: L3 governed AI evaluation

Owner approval: The active completion objective authorizes an evaluation-only
model change after V5 and V7 proved the approved Llama model did not meet the
immutable safe-continuation gate reliably.

Independent review: Required before live calls and final acceptance.

## Goal

Complete AI-008 using a model with stronger instruction-following reliability
while preserving the approved prompt, dataset, evidence, and staged gates.

## Scope

- Add `ai-008-v8` and `golden-evaluation-v8`.
- Reuse the byte-identical V7 prompt and all five/ten/forty-call gates.
- Use evaluation-only model `openai/gpt-4.1-mini`, pinned to OpenAI through
  OpenRouter with zero retries, no fallback, required parameters, denied data
  collection, JSON-object mode, temperature zero, and 1000 output tokens.
- Preserve the production `AI_DEFAULT_MODEL` and all V1-V7 evidence.

## Out of scope

Production prompts or models, API, database, authentication, RAG retrieval,
dataset, CI thresholds, fallback, retries, response healing, and application
dependencies.

## Acceptance and stop conditions

Use dataset fingerprint
`4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
Require 5/5 replay, the existing ten-case canary, and three passing 40-case
runs. Stop V8 permanently on any provider, format, semantic, or evidence
failure. Pricing remains informational and is not written into canonical
metrics.

## Rollback

Revert the scoped V8 commit. No application or database rollback is required.
