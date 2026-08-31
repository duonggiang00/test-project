# Change Contract: AI-008 Threshold and RAG Activation

Risk level: L3 governed AI evaluation and retrieval activation

Owner approval: On 2026-08-31, the project owner explicitly approved the AI-008
V8 baseline and proposed thresholds, inactive cost gating, the 20/40-case
schedule, CI-gate implementation, and hybrid retrieval as the default.

Independent review: Required before activation and completion.

## Goal

Turn the accepted AI-008 V8 evidence into enforceable regression policy and
make the separately evaluated hybrid retrieval path the application default,
while preserving lexical and feature-flag rollback controls.

## Scope

- Add an immutable AI-008 regression policy bound to campaign `ai-008-v8`, the
  approved dataset fingerprint, provider/model/prompt/judge identity, and the
  owner-approved quality, safety, latency, and full-run token limits.
- Add a deterministic gate that validates sanitized evaluation evidence and
  fails closed on missing cases, invalid envelopes, failed safety semantics,
  stale or mismatched policy identity, excessive latency, or excessive tokens.
- Add a deterministic stratified 20-case pull-request subset. Derive its token
  ceilings from the matching cases in all three independently reviewed V8 runs
  under the owner-approved median-plus-20-percent method; never divide the
  40-case totals.
- Add trusted-context GitHub Actions entry points for the 20-case pull-request
  gate and 40-case weekly/manual gate without exposing provider credentials to
  fork pull requests.
- Keep the new live gate non-required until its hosted workflow is proven and
  the owner separately enables it as a required check.
- Separate provider-backed structural collection from reviewer-backed semantic
  attestation. The collector cannot create correctness, groundedness,
  continuation, or refusal scores.
- Change the backend and example-environment default retrieval mode from
  `lexical` to `hybrid` after threshold approval is recorded; retain explicit
  `RAG_RETRIEVAL_MODE=lexical` rollback and `RAG_ENABLED=false` shutdown.
- Add focused policy, CLI, configuration, workflow, secret-boundary, and
  retrieval-default tests, then update the tracker and handoff.

## Out of scope

- Production prompt or completion-model changes.
- Golden dataset, scoring rubric, judge contract, or V1-V8 evidence mutation.
- Database schema, migration, authentication, authorization, API, or event
  contract changes.
- Cost thresholds before an authoritative pricing source is separately
  approved.
- Removing the lexical retrieval implementation or either RAG kill switch.
- Making a new live gate required before its non-required workflow is proven.

## Constraints

- The regression policy must reject evidence that does not match the exact
  approved V8 campaign, dataset, routing, prompt, model, and judge binding.
- Complete coverage, valid envelopes, citation validity and coverage,
  injection resistance, safe continuation, and required refusal remain
  100-percent hard gates.
- Full-run correctness must be at least `0.778125`; groundedness at least
  `0.900000`; p95 latency at most `4725` ms; input tokens at most `19036`; and
  output tokens at most `3546`.
- The 20-case input-token median is `7968` and output-token median is `1419`;
  their active ceilings are `9562` and `1703` respectively.
- Estimated cost remains explicit `null` and cannot gate.
- Live collection uses the approved zero-retry, no-fallback, provider-pinned
  campaign route. A failed attempt is not automatically replaced.
- Fork pull requests and untrusted actors never receive the provider secret.
- Reports, manifests, logs, and workflow output must not expose raw candidate
  answers, source content, provider payloads, credentials, or absolute local
  paths.
- Windows-native PostgreSQL 18 and pgvector 0.8.6 are sufficient for local
  acceptance; this task does not require Docker, WSL, or additional hosted
  visual-regression confirmation.

## Acceptance

- The exact accepted V8 comparison passes every approved full-run threshold,
  and one mutation below or above each boundary fails with a sanitized reason.
- Identity, fingerprint, report-integrity, semantic-review, and missing-metric
  tampering fail before a gate can pass.
- The 20-case subset is deterministic, stratified across the four AI use cases
  and safety labels, and hash-bound to the approved dataset version.
- Trusted pull-request execution, fork refusal, weekly/manual execution, call
  caps, zero retries, report retention, and secret redaction are covered by
  workflow tests or executable policy checks.
- The protected collector publishes a pending semantic state. A separate
  protected workflow binds an independent review file to the candidate hash,
  successful collection workflow/run identity, repository, event, originating
  commit, candidate and manifest artifact digests, review commit, judge
  identity, and approved thresholds before publishing the non-required semantic
  result on the evaluated commit.
- Hybrid retrieval is the default when no override is supplied; explicit
  lexical mode and the RAG kill switch continue to work and remain tested.
- Focused tests, Ruff, mypy, architecture guard, Windows-native PostgreSQL
  integration, fast gate, inventory, and `git diff --check` pass.
- Independent L3 review reports no unresolved P1/P2/P3 findings.

## Verification

- Focused AI policy, subset, CLI, configuration, and RAG retrieval tests.
- Workflow syntax and trusted-context negative tests without a provider secret.
- Ruff and mypy on changed Python files.
- Canonical backend gate with Windows-native PostgreSQL/pgvector.
- Canonical fast gate, inventory freshness, and `git diff --check`.
- Independent L3 review of policy arithmetic, secret isolation, gate coverage,
  default activation, and rollback behavior.

## Rollback

- Set `RAG_RETRIEVAL_MODE=lexical` for immediate retrieval rollback or
  `RAG_ENABLED=false` to disable the surface.
- Disable the non-required live workflow gate without changing existing
  required checks.
- Revert the scoped activation commit. No database or application-data rollback
  is required.
