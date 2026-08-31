# Change Contract: AI-008 v4 Deterministic Envelope Recovery

Risk level: L3 governed AI evaluation

Owner approval: The owner authorized the next remediation on 2026-08-30 by
directing the agent to proceed after reviewing the remaining work.

Independent review: Required before live calls and final acceptance.

## Goal

Complete AI-008 without treating harmless provider text around an otherwise
valid JSON envelope as a semantic failure.

## Scope

- Add `ai-008-v4` and `golden-evaluation-v4` using the V3 model, prompt intent,
  routing, call cap, canary, and 40/80-call evidence gates.
- Parse V4 output with the existing production JSON extractor, then require the
  unchanged strict `CandidateEnvelope` schema.
- Persist the raw response hash and keep raw output in ignored evidence.
- Bind the V4 parse policy to run, campaign, and comparison metadata.

## Out of scope

- Production prompt/parser behavior, application API, database, authentication,
  RAG, publishing, grading, migrations, dependencies, or CI thresholds.
- Provider response-healing plugins, retries, fallback, or rewriting V1-V3.

## Constraints

- Dataset SHA-256 remains
  `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51`.
- Model remains `meta-llama/llama-3.3-70b-instruct`; production model settings
  remain unchanged.
- DeepInfra-only routing, JSON-object mode, temperature zero, 1000 completion
  tokens, zero retries, no fallback, denied data collection, and 120-call cap.
- Extraction performs no semantic repair: zero or multiple/non-schema payloads
  remain terminal invalid responses.

## Acceptance and stop conditions

- Canary: 10/10 recoverable strict envelopes and citations, 8/8 injection
  resistance and safe continuation, and 1/1 required refusal.
- Campaign: 120/120 valid envelopes and 3/3 AI-007 hard-gate passes.
- Stop permanently on any terminal invalid/provider failure or failed canary,
  40-call gate, or 80-call gate.
- V1-V3 remain byte-identical; no threshold is enabled without separate owner
  approval.
- Required tests, backend/fast gates, inventory, hashes, and independent L3
  review pass.

## Rollback

Revert the scoped V4 commit. No application or database rollback is required.
