# Change Contract: AI-001–009 — Governed AI Generation and Evaluation

Risk level: L4 provider/review architecture; L3 sensitive retrieval and grading  
Owner: Primary implementation agent after approval  
Independent review: AI/domain and security reviewers required  
Approval required: Yes  
Approval evidence: Approved by the project owner in
`REMAINING_HIGH_RISK_APPROVAL_PACKET.md` on 2026-08-05; admin golden-dataset
content remains a later required input

## Scope

In scope:

- Provider-neutral generation/streaming boundary and configurable per-use-case
  model policy, initially backed by the current OpenRouter-compatible client.
- Versioned prompts, typed provider results/errors, usage/latency/cost/context
  metadata, and immediate user-visible failure.
- Explicit generation, review, approval/rejection, and publication state.
- Owner-scoped retrieval and protected/redacted AI records.
- Admin-approved golden dataset format, deterministic evaluation runner, and
  governed CI thresholds after an approved baseline exists.
- Proof that AI grading suggestions remain advisory.

Out of scope:

- Automatic provider fallback, autonomous publication/final grading, invented
  “approved” answers, unrestricted raw sensitive logs, cross-owner retrieval,
  or live-provider calls in deterministic CI.

## Verified current behavior and drift

- `material_service.py` owns a module-level synchronous `OpenAI` client and
  hard-coded model in three generation flows.
- `ai_studio_service.py` owns a module-level `AsyncOpenAI` client, hard-coded
  model, inline prompt/tool definitions, and unscoped fallback retrieval of the
  latest document chunks.
- The AI workspace sends `material_id`, but the backend `ChatRequest` declares
  only `messages`; Pydantic currently drops the material identifier and the
  service searches every chunk before falling back to globally latest chunks.
- Provider exceptions are partly sanitized, but no typed provider boundary,
  prompt version, token/cost/latency/context audit record, or configurable model
  policy exists.
- `is_ai_generated` booleans and material `ai_status` cannot express the approved
  review transitions. Save operations can persist generated questions,
  flashcards, and briefs without an approval gate.
- Several material generation paths serialize raw parse/provider exception text,
  and streaming errors use an ad hoc envelope instead of canonical AI codes.
- `grading_service.py` is deterministic answer scoring; there is no separate
  persisted advisory AI-grading suggestion/reviewer state.
- No golden dataset or repeatable correctness/groundedness/injection/cost report
  exists.

## Target architecture and invariants

- A provider protocol accepts typed generate/stream requests and returns typed
  text/tool output, provider/model, token usage, latency, and sanitized failure.
  An OpenRouter adapter contains SDK-specific code. No service imports the SDK.
- A static architecture rule rejects provider-SDK imports outside adapters.
- A `ModelUseCase` policy selects provider/model/config from validated settings
  for chat, question generation, flashcards, briefs, advisory grading, and
  embeddings.
- Prompt templates live in versioned modules with stable IDs. The exact rendered
  prompt is stored only in the approved restricted payload store; core audit
  prefers prompt version and safe source references.
- Each generation job is owner-scoped and transitions only through:
  `requested -> processing -> generated -> awaiting_review -> approved|rejected`,
  then `approved -> published`, with `failed` from execution states. No direct
  generated-to-published transition. Transitions use an allowlist, optimistic
  version, and PostgreSQL row locking.
- Rendered prompt/output lives in a restricted payload record, not the core
  audit event. Provider calls occur outside long database transactions;
  request/completion transitions use separate atomic transactions.
- Publishing and AI-assisted grading require teacher-owner or admin approval.
  The reviewer cannot be inferred from the generation actor.
- Retrieval queries join through the authenticated owner/approved visibility
  scope before selecting chunks. No global “latest chunks” fallback is allowed.
- Provider errors surface immediately as stable application codes without raw
  provider text.
- Chat/generation request schemas require explicit material/source identifiers
  and use Pydantic `extra="forbid"`; unknown fields can no longer disappear
  silently. Streaming events use one documented safe envelope.

## Expected files and contracts

- New `app/ai/` provider protocol, OpenRouter adapter, model policy, prompt
  registry, typed result/error, evaluation, and redaction modules.
- New generation-job/review models and reversible migrations after DATA-001 and
  SEC-002; affected material/question/flashcard/brief/grading schemas/services.
- AI Studio/material routes pass actor and owner scope explicitly. Background
  work opens its own session and operates from an immutable approved job scope.
- Settings add provider/model/use-case configuration without exposing secrets.
- The AI workspace service/hook/preview exposes review state and explicit
  approve/reject/publish actions instead of a direct “save to system” shortcut.

API/event impact:

- Generation responses expose job/review state and safe stable error codes.
- Approval/rejection/publication endpoints are additive and owner/admin guarded.
- AI audit events include prompt version, provider/model, usage, estimated cost,
  latency, context source IDs, reviewer, and outcome. OpenAPI diff requires
  review before snapshot regeneration.

## Golden dataset and evaluation contract

- Versioned JSONL cases contain case ID, use case, safe input/reference context,
  expected answer or rubric, required citations/source IDs, injection label,
  sensitivity classification, and admin approval identity/time/version.
- The validator rejects missing approval metadata, duplicate IDs, unknown source
  references, raw secrets, and unsupported schema versions.
- Agent-authored synthetic cases may test the runner but never count toward the
  required 30–50 admin-approved regression cases.
- The proposed first dataset has 40 reviewed cases: question generation 8,
  flashcards 6, briefs 6, RAG/chat 10, and advisory grading 10, with injection
  cases distributed across applicable groups. The admin may replace this mix.
- Deterministic/replayed evaluation measures answer correctness,
  groundedness/citation validity, context relevance, prompt-injection resistance,
  latency, token usage, and cost. Live-provider benchmarking is a separately
  reported manual/nightly activity, not a deterministic PR dependency.
- AI-008 thresholds are not invented before the first approved baseline. Hard
  safety invariants (cross-owner retrieval, automatic publication/final grading,
  and successful prompt injection) always have zero tolerance; quality/latency/
  cost regression tolerances require the baseline report and owner acceptance.
- Candidate thresholds for that acceptance review are: 100% schema validity,
  tenant isolation, and injection resistance; at least 95% citation validity,
  85% correctness, 90% groundedness, and 85% context relevance; no quality
  regression over three percentage points; cost at most 110% of baseline and an
  approved per-case budget; p95 latency at most 125% of baseline and within an
  approved use-case SLO. These are proposals, not active policy before approval.

## Required order

1. CI-004 migration reliability, DATA-001 audit core, and SEC-002 ownership.
2. AI-001 provider/model policy and contract tests around existing behavior.
3. AI-002 generation/review state and AI-009 advisory-grading enforcement.
4. AI-003 audit metadata using DATA-001.
5. AI-004 redaction/access plus AI-005 owner-safe retrieval.
6. AI-006 dataset schema/validator; pause for 30–50 admin-approved cases.
7. AI-007 baseline report, then owner-approved AI-008 thresholds.
8. Independent AI/security review and completion audit.

## Verification contract

- Provider adapter contract tests for normal/tool/stream/malformed/timeout/rate-
  limit cases with no network.
- Model policy selection and unknown-use-case failure; prompt version snapshot.
- PostgreSQL state-transition race/idempotency, owner/admin review, non-owner
  denial, direct-publication denial, and advisory-grade immutability.
- `AIGradeSuggestion` starts `awaiting_review`; provider completion cannot change
  awarded points, submission totals, or result release. Only owner/admin approval
  applies a suggestion atomically with audit. Existing deterministic objective
  scoring remains automatic and is not reclassified as AI grading.
- Cross-owner retrieval probes, empty-context behavior, prompt-injection corpus,
  redaction/serialization, and audit completeness without sensitive leakage.
- Dataset schema negative fixtures, deterministic evaluation report, repeated-run
  stability, and deliberate threshold-regression failure.
- Latency/token/cost report separated into mocked deterministic and live optional
  evidence; fast/integration/E2E/coverage/OpenAPI/migration gates as applicable.

## Rollback

- Configuration can disable new generation while preserving review/audit rows.
- Revert service wiring to a provider adapter-compatible compatibility path; do
  not bypass review state to recover availability.
- Never delete generated/audit records or downgrade live data merely to roll back
  provider code. Pending jobs become failed/cancelled with an audited reason.
