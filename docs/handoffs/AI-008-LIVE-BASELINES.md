# Handoff: AI-008 Governed Live Baseline Campaign

Status: BLOCKED

Risk level: L3 governed AI evaluation

## Outcome

- Added a capped, resumable, canonical-path live collector for exactly three
  approved 40-case runs and at most 120 provider calls.
- Added strict independent-review binding, sanitized evaluation report
  generation, and a create-only three-run comparison artifact.
- Completed all 120 approved OpenRouter calls without retries. A completed-run
  replay left the 120-reservation ledger hash unchanged and made no new call.
- Independent review covered all 120 answers. The campaign achieved 115/120
  structurally valid responses and 0/3 hard-gate passes, so it is rejected as a
  threshold baseline.
- No CI threshold, application API, database contract, authentication behavior,
  retrieval behavior, or product behavior was changed.

## Evidence

| Evidence | Result |
|---|---|
| Approved dataset | SHA-256 `4de1c805553cdb8bf6b6ac11fc16e372d41cd0b9a99b683020da7749a0e8ee51` |
| Campaign | 120/120 reservations; `baseline-001` through `baseline-003`; no retry and no 121st call |
| Structural format | 38/40, 37/40, and 40/40; aggregate 115/120 |
| Correctness | 0.728125, 0.687500, 0.753125 |
| Groundedness | 0.881250, 0.812500, 0.868750 |
| Citation validity | 0.950000, 0.925000, 1.000000 |
| Injection resistance | 0.875000 in every run; one judged failure per run |
| Hard gates | 0/3 passed |
| p95 latency | 4891 ms, 3609 ms, 4797 ms |
| Cost | Null with 0/120 coverage; no approved price was inferred |
| Focused verification | Ruff passed; Mypy passed; 36 focused tests passed |
| Canonical backend gate | 5/5 passed; 413 unit, 24 contract, and 171 PostgreSQL integration tests; `reports/agent-workflow/ai-008-baseline-final-v2/backend.json` |
| Canonical fast gate | 13/13 passed; 413 backend unit, 24 contract, 182 frontend tests, and production build; `reports/agent-workflow/ai-008-baseline-final-fast/fast.json` |
| Independent L3 review | Approved after adversarial candidate/review/observation/report tamper probes; no unresolved P1/P2/P3 |

Sanitized reports and the comparison are ignored local artifacts under
`backend/reports/ai-evaluation/ai-008-v1/`. Candidate answers and malformed raw
responses are not copied into documentation, stdout, or tracked files.

## Risks and follow-up

- The current model/prompt pair is not safe enough for threshold approval: all
  three runs fail prompt-injection resistance.
- Two runs also fail perfect citation coverage because five provider responses
  did not satisfy the required JSON envelope.
- Context relevance is not production retrieval evidence because this campaign
  supplies the approved sources directly.
- A new campaign needs explicit owner approval because the approved 120-call
  budget is exhausted. It must use a new campaign/prompt version and preserve
  this failed campaign as evidence.
- RAG-SEMANTIC-001 remains downstream and must not use these results as proof of
  retrieval quality.

## Rollback

- Revert the scoped AI-008 tooling commit to remove the collector, review
  binder, comparison tooling, tests, and documentation.
- Ignored campaign artifacts can be retained for audit or removed separately;
  they are not application data and require no database rollback.
