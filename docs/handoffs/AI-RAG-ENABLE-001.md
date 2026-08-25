# Handoff: AI-RAG-ENABLE-001 — Re-enable material RAG chat

Status: DONE
Risk level: L3 — governed sensitive retrieval behavior

## Outcome

- Summary: Owner-scoped material RAG chat is active by default again. The backend and frontend kill switches remain available, the backend remains authoritative, and the compatibility-only mock `/ai/process-document` route stays disabled by default. Existing authentication, ownership isolation, audit metadata, prompt-injection handling, sanitized provider errors, BFF transport, and human-review requirements are preserved.
- Requirements/task IDs: `AI-RAG-ENABLE-001`

## Files changed

- `.env.example` — documents active chat defaults and the default-disabled legacy processor.
- `backend/app/core/config.py` — makes material chat active by default and adds the explicit legacy-process switch.
- `backend/app/api/endpoints/ai_studio.py` — keeps the synthetic compatibility processor behind its own default-off dependency.
- `backend/app/schemas/ai.py` — constrains chat messages to `user`/`assistant`, rejects extra fields, and bounds message/content sizes before service access.
- `backend/app/core/security_guardrails.py` — preserves the same role allowlist for direct service callers as defense in depth.
- `backend/app/services/ai_studio_service.py` — repairs the retained chat audit-metadata type contract.
- `backend/tests/contract/test_rag_feature_flag.py` — covers active defaults, both kill switches, canonical disabled errors, and authentication.
- `backend/tests/unit/test_ai_studio_chat_generator.py` — proves direct callers cannot pass provider-priority roles to the model adapter.
- `backend/tests/test_ai_studio.py` — explicitly opts legacy regression tests into the compatibility processor.
- `backend/tests/test_authorization_idor.py` — explicitly enables both retained routes for owner/cross-owner regression evidence.
- `frontend/src/app/(admin)/ai-workspace/page.tsx` — presents material chat by default while retaining the frontend kill switch.
- `frontend/tests/component/ai-workspace-errors.test.tsx` — covers default-active and explicit-hidden presentation plus interaction states.
- `frontend/tests/e2e/ai-review-flow.spec.ts` — verifies material chat is reachable across the critical four-browser flow.
- `docs/spec/CANONICAL_PROJECT_SPEC.md` — records RAG/material chat as active MVP scope and keeps the mock processor outside that surface.
- `docs/plans/AI-RAG-ENABLE-001_CHANGE_CONTRACT.md` — records approved scope, security boundaries, verification, and rollback.
- `docs/plans/AI-RAG-HIDE-001_CHANGE_CONTRACT.md` and `docs/handoffs/AI-RAG-HIDE-001.md` — record historical supersession without deleting earlier evidence.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — replaces the hide review with the active RAG review item.
- `docs/generated/openapi.json` — records the strict nested chat request contract.
- `docs/generated/project-inventory.json` — regenerated after the scoped source/documentation changes.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `node scripts/verify.mjs fast` | 0 | 495 tests + build | 495 | 0 | 0 | Final environment, branch policy, database drift, inventory, architecture, OpenAPI, Ruff, mypy, backend unit/contract, frontend unit/component, and 23-page production build pass. |
| Focused backend contract/unit tests | 0 | 16 | 16 | 0 | 0 | Active defaults, kill switches, authentication, strict nested-message validation, direct-service role defense, stream envelope, injection guard, and sanitized provider failures pass. |
| Guarded PostgreSQL enabled-path regression | 0 | 3 | 3 | 0 | 0 | Owner chat persists exact redacted audit metadata; student and inactive actors are denied without provider calls; admin cross-owner access records both override and chat audit events; managed test database was dropped. |
| Full guarded PostgreSQL integration | 0 | 171 | 171 | 0 | 0 | The complete PostgreSQL suite passes after the final remediation; the managed test database was dropped. |
| Independent L3 focused rerun | 0 | 16 | 16 | 0 | 0 | The independent reviewer reran the contract/unit scope and granted security/behavior sign-off after both P2 findings were closed. |
| Capped live OpenRouter smoke | 0 | 1 request | 1 | 0 | 0 | Provider abstraction completed one harmless `max_tokens=16` streaming request (`chunks=4`, `characters=3`) without printing credentials or response content. |
| Scoped Ruff | 0 | changed backend/test files | all | 0 | 0 | All checks passed. |
| Expanded AI-module mypy | 0 | 19 modules | 19 | 0 | 0 | The pre-existing retained chat metadata type error is repaired. |
| Focused frontend component test | 0 | 9 | 9 | 0 | 0 | Default-active chat, explicit hide, disabled/enabled controls, sanitized errors, and generation behavior pass. |
| Scoped frontend ESLint | 0 | 2 files | 2 | 0 | 0 | No lint findings. |
| Frontend production build | 0 | 23 generated pages | 23 | 0 | 0 | Compilation, TypeScript, static generation, and build traces pass. |
| `node scripts/verify.mjs architecture` | 0 | 0 active findings | 0 | 0 | 1 waiver | `ARCHITECTURE_OK current=0 baseline=0 waivers=1`. |
| Full mocked Playwright matrix | 0 | 28 | 28 | 0 | 0 | Chromium, Firefox, WebKit, and mobile Chrome pass with no retries. |
| Final mocked Playwright rerun | 1 | 28 | 26 | 2 | 0 | Two unrelated WebKit navigation waits failed after the production build; an isolated no-retry rerun of exactly those registration and AI-flow cases passed 2/2. This run is reported as a pre-existing flake, not as a green matrix. |
| Focused final AI browser flow | 0 | 4 | 4 | 0 | 0 | Final default-active chat assertion passes in all four projects. |
| Chromium AI flow with `--trace=on` | 0 | 1 | 1 | 0 | 0 | A final successful browser trace captures the active material-chat control and governed generation/review flow. |

## Impact

- API/event/schema contract: No route, request, response, OpenAPI, or event-schema changes. Default runtime behavior changes only for `/ai/chat`; the compatibility-only `/ai/process-document` remains default-disabled.
- Migration/data: None. No schema change, data rewrite, or destructive database operation.
- Security/ownership/tenant: Existing owner-scoped queries, indistinguishable cross-owner/missing responses, audit metadata, redaction boundaries, and provider non-invocation guarantees are preserved and reverified on PostgreSQL.
- Dependency/toolchain: No dependency or package-manager change.

## Manual evidence

- Scenario: Load current local backend settings without printing secret values.
- Result: `RAG_ENABLED=True`, `RAG_LEGACY_PROCESS_ENABLED=False`, and `OPENROUTER_API_KEY_CONFIGURED=True`. The production frontend build compiles chat as active when no explicit frontend override exists.
- Scenario: Send one capped harmless prompt through the configured provider abstraction.
- Result: The configured OpenRouter model route returned a four-chunk stream. This verifies one connection/model-route attempt only, not general availability, quality, latency, quota, or cost.
- Screenshot/trace: The final AI flow passed across Chromium, Firefox, WebKit, and mobile Chrome. A successful Chromium trace is available at `frontend/reports/playwright/mocked-results/ai-review-flow-material-up-077e9-e-only-after-review-MOCKED--chromium/trace.zip` (ignored test artifact, not committed).

## Risks and follow-up

- Known risks: Backend and frontend flags can drift, but the backend remains authoritative. The retained legacy processor creates synthetic chunks and therefore remains default-disabled. AI quality is still unmeasured until `AI-006`–`AI-008` are resumed.
- Unverified items: The single capped provider smoke does not establish sustained quota, production latency, answer quality, cost behavior, or semantic retrieval quality.
- Independent review: The L3 reviewer reported no remaining P1/P2 findings. Both initial P2 findings—provider-priority role injection and incomplete PostgreSQL actor/audit evidence—were remediated and independently rechecked.
- Follow-up tasks: Complete `AI-006`–`AI-008` with the approved Vietnamese-first golden dataset, then replace keyword/last-chunk retrieval with the separately approved semantic pgvector path.

## Rollback

- Code: Set `RAG_ENABLED=false` and `NEXT_PUBLIC_RAG_ENABLED=false`, or revert the scoped change, to restore hidden-by-default behavior. Leave `RAG_LEGACY_PROCESS_ENABLED=false` unless explicitly testing compatibility behavior.
- Data: None.
