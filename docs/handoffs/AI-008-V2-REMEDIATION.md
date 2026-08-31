# Handoff: AI-008 v2 Baseline Remediation

Status: BLOCKED

Risk level: L3 governed AI evaluation

## Outcome

- Implemented the approved `ai-008-v2` evaluation-only remediation without
  changing application API, database, authentication, production prompts, RAG
  behavior, publishing, or grading.
- Added strict JSON-object requests, DeepInfra-only routing, required-parameter
  enforcement, data-collection denial, fallback denial, zero SDK retries, and
  runtime attestation that binds those effective settings to campaign metadata.
- Added a deterministic ten-case canary, same-ledger reservation binding,
  create-only review/report evidence, tamper checks, and campaign-bound
  comparison metadata while retaining v1 compatibility.
- Independent pre-call review initially found three enforcement bypasses; all
  were fixed and the final pre-call verdict had no unresolved P1/P2/P3.
- Executed exactly 10 canary calls. Format, citations, injection resistance,
  and the required explicit refusal passed. Safe continuation passed only 3/8,
  so the mandatory stop condition fired and no remaining v2 calls were made.
- No CI threshold was invented or enabled.

## Files changed

- `backend/app/ai/provider.py` — provider-neutral response-format and runtime
  execution-binding contracts.
- `backend/app/ai/openrouter_adapter.py` — optional JSON/routing wire mapping
  and effective policy attestation.
- `backend/app/ai/evaluation/live_baseline.py` — versioned v2 prompt/campaign,
  canary order, cap, ledger, provider, and evidence enforcement.
- `backend/app/ai/evaluation/baseline_canary.py` — strict independent canary
  review and create-only sanitized report.
- `backend/app/ai/evaluation/baseline_comparison.py` — requested-campaign
  binding and explicit v2 metadata with legacy v1 readability.
- `backend/scripts/` — allowlisted v2 collection, canary evaluation, review
  preparation, and comparison entry points.
- `backend/tests/unit/` — provider-wire, cap, ledger, tamper, compatibility,
  campaign-selection, and canary-gate coverage.
- `docs/plans/AI-008_V2_REMEDIATION_CHANGE_CONTRACT.md` — approved scope and
  stop conditions.
- `docs/plans/AI-008_BASELINE_AND_THRESHOLD_PACKET.md` and optimization tracker
  — sanitized decision evidence.

## Verification

| Command/evidence | Result |
|---|---|
| Focused provider/baseline/canary/comparison tests before live calls | 48 passed |
| Targeted Ruff | Passed |
| Targeted Mypy | Passed for 9 files |
| Canonical backend gate | 5/5 passed: 430 unit, 24 contract, 171 PostgreSQL integration; `reports/agent-workflow/ai-008-v2-final-backend/backend.json` |
| Canonical fast gate | 13/13 passed: 430 backend unit, 24 contract, 182 frontend tests, production build; `reports/agent-workflow/ai-008-v2-final-fast-v2/fast.json` |
| Architecture guard | `current=0 baseline=0 waivers=1` |
| Generated inventory | Fresh; 468 files |
| V1 evidence preservation | 14/14 ignored evidence files remain byte-identical by SHA-256 |
| `git diff --check` | Passed |
| Independent pre-call L3 review | Approved; no unresolved P1/P2/P3 |
| Live canary | 10/10 format, 10/10 citations, 8/8 injection resistance, 1/1 required refusal, 3/8 safe continuation; failed |
| Provider-call budget | 10/120 consumed; campaign stopped |

Ignored evidence is under
`backend/reports/ai-evaluation/ai-008-v2/`. It contains the campaign ledger,
ten candidates, independent boolean judgments, and a sanitized report. Raw
candidate content is not copied into tracked files or command output.

## Impact

- API/event/schema contract: none.
- Migration/data: none.
- Security/ownership/tenant: no product-path change; evaluation execution is
  more tightly bound and fail-closed.
- Dependency/toolchain: no dependency added.

## Risks and follow-up

- The fixed v2 model/prompt over-refused or otherwise failed to finish the safe
  task in `brief-006`, `flash-006`, `qgen-006`, `qgen-012`, and `rag-008`.
- V2 must not resume. A v3 prompt/model/campaign requires separate owner
  approval and must preserve both rejected campaigns.
- RAG-SEMANTIC-001 remains downstream; supplied-context evaluation is not proof
  of production retrieval quality.
- Statistical CI thresholds remain inactive until a complete campaign passes
  every hard gate and the owner separately approves the thresholds.

## Rollback

- Revert the scoped v2 tooling commit. There is no API, database, migration, or
  application-data rollback.
- Ignored v2 evidence may be retained for audit. Removing it is a separate
  cleanup action and is not required to roll back application code.
