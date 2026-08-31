# Change Contract: AI-008 v6 Deliverable Contract

Risk level: L3 governed AI evaluation

Owner approval: The active objective authorizes the next version after the
immutable AI-008 v5 failure-replay block.

Independent review: Required before live calls and final acceptance.

## Goal

Produce a new AI-008 baseline campaign that makes question-generation output
and direct-clause refusal placement unambiguous while preserving the V5
failure evidence unchanged.

## Scope

- Add `ai-008-v6` and `golden-evaluation-v6` with the approved model, routing,
  extraction, zero-retry policy, and staged five/ten/forty-call gates.
- Require question-generation answers to contain an explicit source-grounded
  question, never an explanation or unsupported example.
- Require every direct-clause refusal to be the first sentence inside the JSON
  `answer` value.

## Out of scope

Production behavior, API, database, authentication, RAG retrieval, dataset,
CI thresholds, V1-V5 evidence, retries, fallback, response healing, and
application dependencies.

## Acceptance and stop conditions

Use the approved dataset fingerprint
`4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
Require 5/5 replay, then the existing 10-case canary, then three 40-case runs;
stop permanently on any provider, format, semantic, or evidence failure.

## Rollback

Revert the scoped V6 commit. No application or database rollback is required.
