# Agent Workflow Optimization Plan

Status: Active  
Plan owner: Project owner  
Execution owner: Primary coding agent  
Created: 2026-08-05  
Last updated: 2026-08-26
Canonical specification: [`../spec/CANONICAL_PROJECT_SPEC.md`](../spec/CANONICAL_PROJECT_SPEC.md)
Approved remaining-work execution plan:
[`REMAINING_WORK_EXECUTION_PLAN_2026-08-25.md`](REMAINING_WORK_EXECUTION_PLAN_2026-08-25.md)

## 1. Objective

Replace document-only agent guidance with a concise, scoped, reproducible, and executable engineering workflow that:

- Reduces hallucination by grounding work in live code and generated inventory.
- Prevents architectural anti-patterns through CI and static checks.
- Makes local and CI verification reproducible on Windows.
- Provides risk-based agent autonomy and approval boundaries.
- Establishes meaningful unit, integration, E2E, migration, security, and AI evaluation gates.
- Preserves delivery speed for an actively developed MVP.

## 2. Tracking rules

This file is the canonical progress tracker for this optimization program.

Status values:

- `TODO`: Not started.
- `IN_PROGRESS`: Currently owned and being implemented.
- `BLOCKED`: Cannot progress; the blocker must be recorded.
- `REVIEW`: Implementation is complete and awaiting verification/review.
- `DONE`: Acceptance criteria are verified.
- `DEFERRED`: Explicitly postponed with owner approval.

Rules:

1. A task has one implementation owner at a time.
2. At most one task per agent is `IN_PROGRESS` unless parallel work was explicitly assigned.
3. Update task status only with evidence.
4. Record blockers in the task row and in the progress log.
5. Do not mark a milestone complete until all non-deferred tasks are `DONE`.
6. Changes to authentication, migrations, breaking APIs, tenant isolation, or major architecture require owner approval before implementation.

The bounded approval request for the remaining high-risk work is
[`REMAINING_HIGH_RISK_APPROVAL_PACKET.md`](REMAINING_HIGH_RISK_APPROVAL_PACKET.md).
7. Update this tracker in the same change that completes a tracked task.

## 3. Execution order

```text
Milestone 0: Durable specification and plan
    -> Milestone 1: Source of truth and agent rules
    -> Milestone 2: Reproducible toolchain
    -> Milestone 3: Effective CI gates
    -> Milestone 4: Generated inventory
    -> Milestone 5: Test architecture
    -> Milestone 6: Executable anti-pattern checks
    -> Milestone 7: Auth, ownership, and tenant isolation
    -> Milestone 8: Audit, soft delete, and upload governance
    -> Milestone 9: AI reliability and evaluation
    -> Milestone 10: Token-efficient coding workflow
```

Milestones 1 and 2 may partially overlap. Feature development may resume under the new workflow after Milestone 3, while later hardening milestones continue.

### 3.1 Current open work

Verified on 2026-08-27, the milestone tables contain 94 `DONE`, 3 `TODO`,
1 `BLOCKED`, 1 `SUPERSEDED`, and no `REVIEW`, `IN_PROGRESS`, or `DEFERRED`
tasks. The remaining work is:

| Category | IDs | Current evidence | Completion condition |
|---|---|---|---|
| Owner-resumed AI evaluation | AI-006, AI-007, AI-008 | The versioned schema, safe JSONL validator, Ed25519 attestation with an externally pinned owner trust root, complete-distribution check, and 28 focused tests are implemented. The owner approved a Vietnamese-first 40-case design, but no trusted owner/admin key, protected root fingerprint, or signed reference cases exist. | Supply and externally pin the owner trust key, provide 40 signed approved cases, validate them, establish three stable baselines, and add deterministic plus capped live regression tiers. |
| Semantic retrieval | RAG-SEMANTIC-001 | Active chat remains keyword/last-chunk retrieval; local PostgreSQL does not yet provide pgvector. | Install/verify pgvector, pass evaluation gates, implement hybrid retrieval with lexical rollback, and remove the approved legacy endpoint. |

## 4. Milestone 0 — Durable specification and plan

Goal: Save all confirmed decisions and the implementation backlog before changing workflow behavior.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| PLAN-001 | Create the canonical confirmed project specification | DONE | — | Spec exists, is English, and covers all approved answers |
| PLAN-002 | Create this task-level implementation plan and tracker | DONE | PLAN-001 | Tasks have IDs, dependencies, statuses, and acceptance criteria |
| PLAN-003 | Validate links, decision coverage, dependency order, and repository diff | DONE | PLAN-001, PLAN-002 | Link and consistency checks pass; no application code changed |

Exit criteria:

- Confirmed requirements are durable and reviewable in Git.
- Future tasks reference this plan and specification rather than conversation history.

## 5. Milestone 1 — Source of truth and agent rules

Goal: Remove contradictory, duplicated, and stale instructions from the default agent context.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| GOV-001 | Create accepted ADRs for PostgreSQL, SQLAlchemy 2.x, transactions/UoW, BFF auth, frontend state, brutalist design, AI abstraction, and spec-drift policy | DONE | PLAN-003 | Each decision has status and supersession rules |
| GOV-002 | Create the canonical permission matrix and ownership policy | DONE | GOV-001 | Resource/action policies cover admin, owner teacher, non-owner teacher, and student |
| GOV-003 | Define canonical error and audit-event contracts | DONE | GOV-001 | Schemas and localization boundary are documented |
| GOV-004 | Create canonical root `AGENTS.md`; retire the protected historical `.agents/AGENTS.md` under GOV-012 | DONE | GOV-001–003 | No framework duplication; source order and approval boundaries are clear |
| GOV-005 | Create or rewrite scoped backend agent instructions | DONE | GOV-004 | Backend rules cover SQLAlchemy 2.x, transaction ownership, RBAC, audit, tests |
| GOV-006 | Rewrite scoped frontend agent instructions | DONE | GOV-004 | Frontend rules cover BFF, Server Components, SWR, Zustand, brutalist tokens |
| GOV-007 | Create scoped backend and frontend test instructions | DONE | GOV-004 | Test changes and verification tiers are explicit |
| GOV-008 | Introduce L0–L4 task risk classification | DONE | GOV-004 | Approval/reviewer requirements are unambiguous |
| GOV-009 | Create Evidence Packet, Change Contract, and Handoff templates | DONE | GOV-008 | Templates are concise and reusable |
| GOV-010 | Consolidate overlapping frontend skills into architecture and design skills | DONE | GOV-005–009 | `frontend-architecture` and `build-brutalist-ui` pass the official skill validator; legacy overlap is outside discovery |
| GOV-011 | Refocus clean-architecture skill on backend architecture | DONE | GOV-005–009 | `backend-architecture` passes the official skill validator and matches the approved backend contracts |
| GOV-012 | Archive historical worker/auditor/handoff context outside default discovery | DONE | GOV-010, GOV-011 | 167 legacy files remain recoverable at `.legacy-archive/antigravity-agents-20260805` and are ignored by Git |
| GOV-013 | Replace manual project snapshots with links to canonical docs pending generated inventory | DONE | GOV-012 | The active `.agents` tree contains no manual `PROJECT_STATE.md`; root/scoped instructions link to canonical documents |

Exit criteria:

- No active rule conflicts about fonts, colors, routes, auth storage, or data fetching.
- Agents load only scope-relevant instructions.
- Risk and approval boundaries are operationally clear.

## 6. Milestone 2 — Reproducible toolchain

Goal: Make the same verification commands work on Windows and GitHub Actions.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| TOOL-001 | Migrate backend dependencies to `pyproject.toml` and `uv.lock` | DONE | PLAN-003 | Clean Windows bootstrap installs locked dependencies |
| TOOL-002 | Pin the supported Python version | DONE | TOOL-001 | Local and CI report the same supported version |
| TOOL-003 | Separate production and development/test dependencies | DONE | TOOL-001 | Runtime install excludes test-only tools; CI dev install succeeds |
| TOOL-004 | Enforce npm and a supported Node version | DONE | PLAN-003 | `engines`/version file and lockfile policy are documented and checked |
| TOOL-005 | Normalize environment configuration and `.env.example` | DONE | TOOL-001 | Env validator passes with seven canonical keys; backend settings and BFF URL tests pass without committed secrets |
| TOOL-006 | Create cross-platform `verify:fast`, backend, frontend, integration, E2E, and all entry points | DONE | TOOL-001–005 | `scripts/verify.mjs` exposes all required modes; fast and integration modes pass on Windows and Playwright discovers four E2E tests |
| TOOL-007 | Remove dependency on checked-in/cross-platform-incompatible virtual environments | DONE | TOOL-006 | Shared commands invoke locked uv environments and local Node tools; no bootstrap command references `backend/venv` or global pytest |
| TOOL-008 | Prepare an isolated PostgreSQL integration profile | DONE | TOOL-001, TOOL-005 | Guarded lifecycle created `test_project_db_test`, passed 24 integration tests, dropped it in `finally`, and final status was `absent` |
| TOOL-009 | Document a future containerization path without making Docker mandatory | DONE | TOOL-008 | `docs/development/CONTAINERIZATION_PATH.md` defines future service/image/runtime contracts while preserving the Windows-native workflow |
| TOOL-PYTEST-CACHE-001 | Make coverage independent of pytest cache accessibility | DONE | TOOL-006, TEST-001 | Both coverage phases disable the cache provider, create report output first, propagate failures, and the canonical coverage gate passes 672 tests at 90.57% backend/61.25% frontend |

Exit criteria:

- A clean Windows checkout can install and run fast verification.
- Local and CI use the same logical entry points.

## 7. Milestone 3 — Effective CI gates

Goal: Prevent unverified code from entering `main`.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| CI-001 | Fix `.gitignore` so backend and frontend test suites are tracked | DONE | PLAN-003 | `git check-ignore` confirms test files are not ignored |
| CI-002 | Add pull-request fast gate | DONE | TOOL-006, CI-001 | GitHub PR run `32837826190` completed `Fast verification` successfully |
| CI-003 | Add push-to-main integration gate | DONE | TOOL-006, TOOL-008, CI-001 | GitHub push run `32831201837` completed `PostgreSQL integration`, including coverage and the Alembic round trip, successfully |
| CI-004 | Add Alembic upgrade/downgrade/upgrade verification | DONE | CI-003 | Guarded PostgreSQL passes `upgrade head -> downgrade base -> upgrade head`; exact table/enum/revision assertions, single-head signature validation, nine runner unit tests, and `_test` cleanup pass after separately approved FK-name repairs |
| CI-005 | Add mocked Playwright critical-flow suite to PRs | DONE | CI-002 | GitHub PR run `32837826190` completed the 28-test Chromium/Firefox/WebKit/mobile matrix and owner/flake policy successfully |
| CI-006 | Add real-backend/PostgreSQL smoke E2E suite on `main` | DONE | CI-003, CI-005 | GitHub push run `32831201837` completed `Real backend smoke E2E` successfully with the isolated PostgreSQL service |
| CI-007 | Add Chromium, Firefox, WebKit, and mobile projects | DONE | CI-005, CI-006 | Chromium, Firefox, WebKit, and Pixel 7 Chrome matrix passes locally in 52s, within the 10-minute budget |
| CI-008 | Upload logs, traces, screenshots, and reports on failure | DONE | CI-005 | Local failures produced error context/screenshot/video; config captures first-retry trace and CI uploads the complete Playwright report tree |
| CI-009 | Add flaky-test retry/ownership policy | DONE | CI-005 | One retry collects diagnostics; report checker fails retried/flaky/unowned tests and the synthetic violation fixture fails as expected |
| CI-010 | Protect required checks before merge | DONE | CI-002–009 | `main` protection requires the exact three PR contexts with strict/up-to-date checks, denies force pushes/deletion, and left PR #1 `unstable` while its mocked check failed |
| SEC-CSP-001 | Narrow the production CSP while preserving static rendering | DONE | CI-002, TEST-007 | Production removes `unsafe-eval` and unused external origins, development alone retains `unsafe-eval`, HTTP captures match the contract, fast/build pass, and mocked E2E passes 28/28 |

Exit criteria:

- CI runs on pull requests and pushes to `main`.
- Backend tests are actually executed.
- Required checks prevent unverified merges.

## 8. Milestone 4 — Generated inventory and hallucination controls

Goal: Replace manually maintained technical snapshots with code-derived facts.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| INV-001 | Generate SQLAlchemy model and relationship inventory | DONE | TOOL-006 | Runtime introspection emits 13 mapped models with columns and relationships deterministically |
| INV-002 | Generate Pydantic schema and FastAPI route/dependency inventory | DONE | INV-001 | Runtime inventory captures 67 schemas and all 62 OpenAPI operations, including lazy included routers |
| INV-003 | Generate Next.js route, hook, service, and protected-layout inventory | DONE | TOOL-006 | Filesystem inventory matches all 25 live `page.tsx` routes and records layouts, hooks, services, and BFF routes |
| INV-004 | Generate test inventory and coverage metadata | DONE | INV-001–003 | Backend/frontend test locations, tiers, counts, providers, and baseline state are machine-readable |
| INV-005 | Attach commit SHA, Alembic head, timestamp, and generator version | DONE | INV-001–004 | Provenance includes generation commit/time, Alembic head, generator version, and a verified relevant-source hash |
| INV-006 | Create a Windows-friendly feature context command | DONE | INV-005 | `node scripts/project-inventory.mjs context <term>` validates freshness and returns scoped JSON |
| INV-007 | Reduce `PROJECT_STATE.md` to capabilities, blockers, active transitions, and canonical links | DONE | INV-005 | No active `PROJECT_STATE.md` or hand-maintained route/model/hook snapshot remains; canonical links are in scoped instructions |
| INV-008 | Add CI check that generated inventory is current when relevant source changes | DONE | CI-002, INV-005 | Inventory check is part of the shared fast gate; an injected source probe produced the expected stale failure |

Exit criteria:

- Technical facts are derived from live code.
- Inventory trust is tied to the current commit rather than an age window.

## 9. Milestone 5 — Test architecture

Goal: Establish fast feedback and meaningful coverage across risk boundaries.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| TEST-001 | Measure backend and frontend coverage baselines | DONE | CI-002, CI-003 | Reproducible full-source runs record backend 72.52% (1,639/2,260) and frontend 0.75% (81/10,685) line coverage |
| TEST-002 | Prevent coverage regression and target ~80% on new/changed code | DONE | TEST-001 | Local/CI checker forbids baseline drops and enforces an 80% executable changed-line target when a base SHA is available |
| TEST-003 | Separate backend unit, contract, and PostgreSQL integration suites | DONE | CI-003 | Marker collection partitions 41 tests into 14 unit, 3 contract, and 24 integration cases; contract suite passes independently |
| TEST-004 | Add ownership and tenant-isolation negative-test matrix | DONE | TEST-003, GOV-002 | PostgreSQL matrices cover anonymous, student, owner/non-owner teacher, admin override, legacy-null, IDOR equivalence, cross-resource links, retained records, audit atomicity, concurrency, and query ceilings |
| TEST-005 | Expand query-budget tests for important list/detail endpoints | DONE | TEST-003 | PostgreSQL regression compares exam detail with 2 vs 10 nested questions; both stay within four queries and the larger result does not add queries |
| TEST-006 | Separate frontend unit, component, mocked E2E, and real E2E suites | DONE | CI-005, CI-006 | Unit, component, mocked four-browser, and guarded real-backend suites have explicit commands; all four tiers pass independently |
| TEST-007 | Add hydration, cache-mutation, and BFF-only tests | DONE | TEST-006 | Five frontend unit suites pass 13 tests including Zustand no-token hydration, SWR non-revalidating cache mutation, and BFF cookie/path/host/redirect contracts |
| TEST-008 | Add brutalist visual regression coverage | DONE | TEST-006, CI-007 | Reviewed black/white desktop/mobile baselines exist for all four browser projects; tooling overlay removed and clean matrix passes 4/4 |
| TEST-009 | Cover loading, empty, error, disabled, and keyboard states | DONE | TEST-006 | Five component tests cover loading/error/empty/disabled/focus semantics and mocked flow proves keyboard activation across four browser projects |
| UI-LANGUAGE-001 | Convert remaining executable frontend UI text and comments to English | DONE | SEC-CSP-001 | All 37 identified source files are translated; the source scan has zero unintended Vietnamese UI/comment matches; Windows/Linux visual evidence passes; independent review approved |
| TEST-FE-COVERAGE-001 | Raise meaningful frontend coverage while translating each wave | DONE | TEST-002, UI-LANGUAGE-001 | Six behavior-oriented suites raise all-source coverage to 76.97% and changed-line coverage to 82.14%; canonical fast gate and independent review pass |

Exit criteria:

- Test tiers match change risk.
- Coverage cannot silently decline.
- Query, ownership, and browser risks have explicit tests.

## 10. Milestone 6 — Executable anti-pattern prevention

Goal: Convert critical architecture rules into failing checks.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| GUARD-001 | Add Python lint/type baseline | DONE | TOOL-006 | Ruff syntax/name checks pass across app/scripts/tests; mypy passes the five explicitly typed config/security/runner modules; both run in fast verification |
| GUARD-002 | Reject new `Session.query()`, `datetime.utcnow()`, bare exceptions, and raw error messages | DONE | GUARD-001 | Good/bad fixtures pass their meta-test and a temporary live `Session.query()` probe fails the baseline check |
| GUARD-003 | Detect queries in loops and request sessions passed to background tasks | DONE | GUARD-001 | Dedicated fixture rules detect loop queries and session arguments inside balanced `add_task(...)` calls without cross-function false positives |
| GUARD-004 | Enforce router/use-case/repository dependency direction | DONE | GOV-005, GUARD-001 | Layer-import fingerprints are baselined and invalid-import fixture is rejected |
| GUARD-005 | Reject browser calls that bypass the BFF | DONE | GOV-006, CI-002 | Direct backend-origin browser fixture is rejected; BFF handler files are the explicit exception |
| GUARD-006 | Reject component data fetching, token local storage, server state in Zustand, and reload-based mutations | DONE | GOV-006, CI-002 | All four frontend anti-pattern families have failing fixtures and new fingerprints fail fast verification |
| GUARD-007 | Enforce trailing-slash and route conventions | DONE | GOV-005, GOV-006 | Backend decorators and frontend service/hook paths are scanned; both violation fixtures are detected |
| GUARD-008 | Enforce local font and black/white design-token policy | DONE | GOV-006 | Remote-font, icon-font, gradient, named-color, color-function, and non-monochrome literal fixtures are detected; current executable design debt is zero |
| GUARD-009 | Generate and diff OpenAPI contracts | DONE | CI-002, INV-002 | Deterministic runtime OpenAPI snapshot covers all registered paths and fails fast verification on any unreviewed diff; breaking-change approval remains explicit |
| GUARD-010 | Detect model changes without migrations | DONE | CI-004, INV-001 | Runtime SQLAlchemy hash is bound to Alembic heads; model-only changes fail and the generator refuses to bless them without a new head |

Exit criteria:

- Critical anti-patterns fail locally and in CI.
- Rules no longer claim enforcement that tests do not provide.

## 11. Milestone 7 — Authentication, ownership, and tenant isolation

Goal: Secure current behavior and prepare clean admin/teacher separation.

All tasks in this milestone require approved change contracts and independent review.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| SEC-001 | Implement named permission-policy layer | DONE | GOV-002, TEST-004 | Typed policies centralize compatibility grants, owner decisions, admin override, and fail-closed audit commits |
| SEC-002 | Define and apply ownership fields and filters to sensitive resources | DONE | SEC-001 | Explicit/derived ownership, scoped queries, legacy-null quarantine, same-owner links, and tenant-safe retrieval pass PostgreSQL tests |
| SEC-003 | Implement access/refresh token lifecycle and rotation | DONE | GOV-001, TEST-003 | Fifteen-minute access tokens plus hashed opaque refresh sessions, 7/30-day expiry, atomic rotation, and replay-family revocation pass PostgreSQL tests |
| SEC-004 | Implement revocation and logout semantics | DONE | SEC-003 | Logout, logout-all, password-change, inactive-user, and replay revocation behavior is tested and security-sensitive events are audited |
| SEC-005 | Implement CSRF protections for cookie-authenticated mutations | DONE | SEC-003 | Same-origin enforcement, constant-time double-submit CSRF checks, BFF credential stripping, and cross-site rejection cases pass |
| SEC-006 | Add IDOR and cross-tenant regression suite | DONE | SEC-002–005 | Ownership/IDOR matrices pass; the owner approved student-only self-service with separate audited Admin management contracts, and the permission matrix/tests match that decision |
| SEC-007 | Verify canonical role redirects and frontend UX guards | DONE | SEC-001, TEST-006 | Server-side `/auth/me` role hydration and canonical `/dashboard`, `/student/home`, and `/login` redirects pass unit, mocked-browser, and real-backend E2E coverage |

Exit criteria:

- Backend ownership enforcement is complete for scoped resources.
- Auth lifecycle and cross-tenant negative tests pass.

## 12. Milestone 8 — Audit, soft delete, and upload governance

Goal: Make sensitive actions traceable and deleted data recoverable for 30 days.

Migration tasks require owner approval and downgrade evidence.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| DATA-001 | Implement canonical audit-event model/service | DONE | GOV-003, CI-004 | Migration round trip and audit schema tests pass |
| DATA-002 | Instrument admin/teacher, exam, grading, AI, restore, purge, and auth events | DONE | DATA-001 | Exam/topic/question/material/flashcard CRUD, publish/unpublish, grading, restore, and purge actions commit one redacted audit event atomically with their business mutation; `ai.*` events remain separate follow-up work under AI-003 |
| DATA-003 | Implement reusable soft-delete fields and query policy | DONE | GOV-002, CI-004 | `SoftDeleteMixin` plus a single `do_orm_execute`/`with_loader_criteria` listener exclude deleted rows from every default read for the five governed roots; migration downgrade refuses while any row is soft-deleted |
| DATA-004 | Implement admin/owner restoration policy | DONE | DATA-003, SEC-002 | Admin/owner-teacher restore within the exact 30-day window passes a five-actor matrix; non-owner/student/anonymous denied; expired window returns a stable 409 |
| DATA-005 | Implement 30-day purge service with dry run and audit | DONE | DATA-002–004 | Allowlisted to soft-deleted `StudyMaterial` only (User/Exam/Question/Topic/audit_events structurally unreachable); dry-run/apply/reconcile CLI; two-phase file quarantine with a persistent `purge_jobs` ledger for crash-window recovery |
| DATA-006 | Confirm separate retention for submissions, grades, and sensitive AI logs | DONE | DATA-001 | Owner-approved policy is recorded before permanent purge |
| DATA-007 | Introduce local storage interface for uploaded files | DONE | GOV-001 | Injected `FileStorage` protocol preserves local behavior with atomic, UUID-named writes and root-confined deletion; fast and PostgreSQL gates pass |
| DATA-008 | Enforce PDF/DOCX/PPTX/TXT and 50 MB validation | DONE | DATA-007 | 17 focused cases cover extension, MIME, PDF/OOXML signature, UTF-8 text, size, collision, atomic-failure cleanup, DB rollback, and path boundaries; endpoint reads at most 50 MB + 1 byte |
| DATA-009 | Apply owner/admin authorization and 30-day lifecycle to files | DONE | DATA-003–005, DATA-007 | Owner/admin download boundary landed in Batch B; a soft-deleted material's file now survives to its restore or purge instead of being deleted at soft-delete time; full lifecycle (active/soft-deleted/restored/purged) proven cross-owner-indistinguishable at every stage |

Exit criteria:

- Required actions are auditable.
- Applicable deleted data is recoverable for 30 days.
- File handling matches the approved contract.

## 13. Milestone 9 — AI reliability and evaluation

Goal: Ensure AI output is reviewable, tenant-safe, measurable, and regression-tested.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| AI-001 | Introduce provider abstraction and use-case model policy | DONE | GOV-001 | Typed provider protocol with an OpenRouter adapter as the only SDK import site (enforced by a non-baselined architecture rule); `ModelUseCase` resolves provider/model from validated settings; prompts are versioned modules with stable ids |
| AI-002 | Implement generation and approval state machine | DONE | DATA-001 | `AIGenerationJob` enforces the §9.2 states via an allowlist with no `generated -> published` pair, optimistic `version`, and row locking; the `save-*` direct-write routes were removed and both background workers now park drafts; full-stack including the review UI and the §10.3 review E2E flow |
| AI-003 | Implement prompt versioning and AI audit metadata | DONE | AI-001, DATA-001 | Every transition and chat call records the §2.4 field set (prompt version, provider/model, tokens, estimated cost, latency, context source ids, reviewer, outcome) atomically with the state change; cost is configuration-derived or an explicit null, never fabricated |
| AI-004 | Add redaction and access controls for sensitive AI logs | DONE | AI-003, SEC-002 | Rendered prompts/raw output live only in `ai_restricted_payloads`, readable by owner/admin with cross-tenant probes indistinguishable from missing; a planted canary reaches no audit row; §6.3's 30-day expiry runs through the existing purge path without loosening its allowlist |
| AI-005 | Enforce tenant-safe retrieval | DONE | SEC-002, TEST-004 | AI chat/process/background generation require one authorized material and cross-owner/missing probes never invoke the provider or enter retrieval context |
| AI-006 | Build the first admin-approved golden dataset | BLOCKED | AI-001 | The v1 strict schema/validator, canonical fingerprint, safe CLI, externally pinned Ed25519 trust-root verification, complete 16/12/6/6 distribution check, and 28 focused tests pass. Completion requires an owner-controlled key, protected approved root fingerprint, and 40 signed owner/admin-approved reference cases; none is configured. See `../handoffs/AI-006-DATASET-VALIDATOR.md` |
| AI-007 | Implement correctness, groundedness, citation, relevance, injection, latency, and cost evals | TODO | AI-006 | Versioned evaluator emits aggregate/per-case metrics without committing raw provider payloads; structure, citation, and injection remain hard gates |
| AI-008 | Add prompt/model regression thresholds to CI | TODO | AI-007 | After three stable full baselines, deterministic PR checks and a capped 20-case live subset enforce approved thresholds while all 40 run weekly/manual |
| AI-009 | Verify AI grading remains advisory until teacher/admin approval | DONE | AI-002, AI-007 | `AIGradeSuggestion` starts `awaiting_review` and its creation cannot change awarded points, submission totals, or result release; the existing deterministic `GradingService` is untouched and not reclassified. No AI grading exists yet, so the invariant is established ahead of it rather than retrofitted |
| AI-RAG-HIDE-001 | Temporarily disable RAG/material chat while preserving content generation | SUPERSEDED | AI-001–005 | Implemented and verified, then superseded by the owner's 2026-08-25 decision to return RAG/material chat to the active MVP surface; retained as historical evidence |
| AI-RAG-ENABLE-001 | Re-enable owner-scoped RAG/material chat by default | DONE | AI-001–005 | Material chat defaults are active while the backend-authoritative kill switch, default-disabled legacy mock processor, strict message-role contract, owner-scoped retrieval, audit metadata, prompt-injection handling, sanitized errors, and BFF transport remain; fast passes 495 tests plus build, full guarded PostgreSQL passes 171/171, capped live provider smoke passes, and independent L3 review reports no remaining P1/P2 |
| RAG-SEMANTIC-001 | Replace lexical-only retrieval with evaluated pgvector hybrid retrieval | TODO | AI-006–008 | Typed embeddings, pgvector storage/indexing, vector-plus-full-text reciprocal-rank fusion, source events, lexical rollback, and approved `/ai/process-document` removal pass safety/quality thresholds before semantic mode becomes default |

Exit criteria:

- AI changes are measurable and auditable.
- Sensitive retrieval is tenant-isolated.
- All AI-generated publishable content requires human approval.

## 14. Milestone 10 — Token-efficient coding workflow

Goal: Reduce routine coding context and stdout without weakening approvals, review, or verification coverage.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| TOK-001 | Establish workflow-token governance and six fixed scenarios | DONE | GOV-008, TEST-001 | L2 Change Contract and six L0-L3 benchmark scenarios record context, commands, stdout proxies, elapsed time, and required gates |
| TOK-002 | Apply progressive disclosure and compact task briefs | DONE | TOK-001 | Root/scoped rules load relevant policy, centralize the verification matrix, and apply the six-field brief plus risk-based artifact policy |
| TOK-003 | Add a bounded live task-context packet | DONE | INV-001-008, TOK-002 | Live source lookup works with stale inventory, labels freshness, maps rules/spec/ADRs/code/tests/dependencies, and remains deterministic within 12 KB/180 lines |
| TOK-004 | Add compact verification, persisted logs, and safe resume | DONE | TOOL-006, TOK-001 | Compact/verbose output, redacted ignored logs/manifests, failure tails, exact fingerprints, and non-cacheable gate exclusions pass focused and canonical verification |
| TOK-005 | Record risk-based model routing and benchmark proxy results | DONE | TOK-001-004 | Routing preserves required reviewers; six-scenario median L0-L2 context reduction is 79.71%; actual token telemetry is explicitly unverified |

Exit criteria:

- Every L0-L2 context packet is at most 12 KB and 180 lines.
- Median context plus successful-output proxies improve by at least 40% without losing a gate or test.
- Independent L2 review confirms failures remain visible and application/API/database behavior is unchanged.

## 15. Agent assignment model

| Change class | Implementation | Review | Prior approval |
|---|---|---|---|
| Documentation/rules | One primary agent | Self-review or lightweight review | No |
| Small UI/hook/service | One primary agent | Self-review | No |
| Endpoint or cross-layer feature | One owner | Independent diff review | Only if contract changes |
| Migration | Backend/data specialist | Independent data review | Yes |
| Authentication/RBAC/tenant isolation | Security/backend specialist | Independent security review | Yes |
| AI grading or sensitive retrieval | AI/backend specialist | Domain and security review | Yes |
| CI/tooling | Platform owner | Independent review | Required-gate changes only |

The reviewer must not silently take ownership of a large implementation rewrite. Material rework returns to the implementation owner or becomes a separately tracked follow-up.

## 16. Definition of Done

A task may move to `DONE` only when its handoff records:

- Summary and requirement/task IDs.
- Files changed.
- Commands executed and exact relevant results.
- Tests collected, passed, failed, and skipped.
- Contract and migration impact.
- Security, ownership, and tenant impact.
- Manual verification performed.
- Screenshots/traces for UI work.
- Known risks and unverified items.
- Rollback instructions when applicable.

If the environment cannot execute a required check, the task remains `BLOCKED` or `REVIEW`; it is not `DONE`.

## 17. Current progress log

| Date | Task | Event | Evidence/notes |
|---|---|---|---|
| 2026-08-05 | PLAN-001 | Completed | Confirmed specification saved in `docs/spec/CANONICAL_PROJECT_SPEC.md` |
| 2026-08-05 | PLAN-002 | Completed | Task-level plan and tracker saved with 87 task rows |
| 2026-08-05 | PLAN-003 | Completed | Canonical link, decision coverage, status vocabulary, encoding, and scoped worktree validated |
| 2026-08-05 | GOV-001 | Completed | Eight accepted ADRs created and structurally validated in `docs/adr/` |
| 2026-08-05 | GOV-002 | Completed | Approved target policy, compatibility transition, ownership evaluation, and negative-test matrix documented |
| 2026-08-05 | GOV-003 | Completed | Stable error shape, localization boundary, audit event schema, privacy rules, and required contract tests documented |
| 2026-08-05 | GOV-004–009 | Completed | Canonical root/scoped rules, L0–L4 classification, and evidence/change/handoff templates created and validated |
| 2026-08-05 | CI-001 | Completed | Backend/frontend tests are trackable; local DB, environment, and build artifacts remain ignored |
| 2026-08-05 | TOOL-004 | Completed | npm 10 policy, Node 22 local selector, supported engine range, strict engine checks, and lock metadata validated |
| 2026-08-05 | TOOL-001–003 | Completed | Python 3.12 uv project/lock created, 65 packages installed, runtime imports passed, dev dependencies separated, and 24 official tests collected |
| 2026-08-05 | GOV-010–013 | Completed | Archived 167 Antigravity legacy files outside discovery; created and officially validated three focused project skills; retired the manual project snapshot |
| 2026-08-05 | TOOL-005–007 | Completed | Canonical env contract added; shared Windows/CI verification added; fast gate passed in 44.8s, backend passed 29/29, integration passed 24/24, frontend passed 9/9 plus production build |
| 2026-08-05 | Repository hygiene | Completed | Archived the nested frontend Git metadata with 47 files and changed the unborn root branch from `master` to canonical `main` |
| 2026-08-05 | TOOL-008 | Completed | Safety/unit suite passed 14/14; isolated PostgreSQL lifecycle passed 24/24 and confirmed the test database was absent after cleanup |
| 2026-08-05 | TOOL-009 | Completed | Optional service, image, configuration, startup, health, storage, test-profile, and adoption contracts documented without requiring Docker |
| 2026-08-05 | CI-002–003 | Review | Replaced legacy CI with read-only fast and PostgreSQL integration jobs; workflow YAML parses, local gates pass, and failure reports are produced; GitHub run is unavailable because the root repository has no remote |
| 2026-08-05 | CI-004 | Blocked | Guarded migration runner cleaned up correctly but `upgrade head` failed in the initial migration at `DROP INDEX ix_user_email`; no migration assertion or history was modified |
| 2026-08-05 | INV-001–008 | Completed | Generated inventory records 13 models, 67 schemas, 62 API operations, 25 pages, frontend modules, and test metadata; counts matched OpenAPI/filesystem, context output parsed, deterministic rerun passed, and an injected source probe triggered the stale gate |
| 2026-08-05 | TEST-001–002 | Completed | Isolated backend processes passed 14 unit + 24 integration tests at 72.52%; all-source frontend run passed 9 tests at an honest 0.75%; baseline gate passed and the elevated-regression fixture failed as expected; CI YAML parses with PR and push coverage jobs |
| 2026-08-05 | TEST-003 | Completed | Collection proved a disjoint 14 unit + 3 contract + 24 integration partition equal to all 41 cases; OpenAPI path/ID/tag and error-envelope contracts passed 3/3 without PostgreSQL |
| 2026-08-05 | TEST-005 | Completed | Guarded PostgreSQL query-budget regression passed for 2 vs 10 nested questions/options; both requests stayed at or below four queries and larger cardinality did not increase query count |
| 2026-08-05 | TEST-004 | Blocked | Five-actor exam update matrix is executable; target assertions expose non-owner access to bulk question assignment and material detail, retained as strict expected failures pending approved SEC-001/002 implementation |
| 2026-08-05 | CI-005/007–009 | Completed/Review | Mocked admin flow now authenticates and intercepts BFF-shaped contracts without backend access; Chromium/Firefox/WebKit/mobile pass 4/4 in 52s; failure artifacts were inspected; flaky/unowned fixture fails policy; PR job awaits its first GitHub run |
| 2026-08-05 | TEST-006 | Blocked | Unit, component, mocked E2E, and real E2E have distinct commands/configs; 2 component tests and 4 mocked browser projects pass, while real-backend CI remains CI-006 |
| 2026-08-05 | CI-006 / TEST-006 | Completed/Review | Guarded real runner used backend port 8765, seeded only test users, passed setup + student topic/exam/submit/result/cleanup 3/3 in 32.3s, passed owner/flake policy, and confirmed `_test` database cleanup; GitHub `main` execution remains pending |
| 2026-08-05 | GUARD-002–008 | Completed | Static gate baselined 247 legacy fingerprints, compliant fixtures produced 0, bad fixtures exercised 17 rule families, a temporary live `Session.query()` probe failed as expected, and false-positive background-task matching was removed with balanced-call parsing |
| 2026-08-05 | GUARD-001 | Completed | Added locked Ruff 0.16.1 and mypy 1.20.2; Ruff passed app/scripts/tests and mypy passed five explicit typed boundary modules after three evidence-based type fixes |
| 2026-08-05 | GUARD-009 | Completed | Deterministic runtime OpenAPI snapshot/check added to fast verification; any path/method/schema/security diff now fails before regeneration and retains breaking-change approval rules |
| 2026-08-05 | GUARD-010 | Completed | Runtime signature binds 13 SQLAlchemy models to current Alembic heads; model-only drift fails and cannot be regenerated without a head change; migration history remains untouched |
| 2026-08-05 | TEST-007 | Completed | Frontend unit suite expanded from 9 to 13 passing tests; new cases verify user hydration without token storage, SWR cache mutation without a second transport call, and BFF authorization/path/host/redirect behavior |
| 2026-08-05 | TEST-008–009 | Completed | Reviewed four black/white topics-page PNG baselines at desktop/mobile sizes, removed Next dev overlay noise, clean visual matrix passed 4/4 in 45.9s, and component suite covers loading/error/empty/disabled/focus while the browser flow activates via Enter |
| 2026-08-05 | DATA-007–008 | Completed | Material uploads now use an injected local-storage boundary with atomic UUID writes and root-confined deletion; PDF/DOCX/PPTX/TXT validation enforces MIME, signature/OOXML structure, UTF-8 text, safe paths, and a 50 MB limit; 17 focused tests, 3/3 PostgreSQL material tests with cleanup, and the 83.5s fast gate pass |
| 2026-08-05 | CI-010 | Review | Added a machine-readable `main` protection policy, workflow-drift checker, and application/negative-proof checklist; no Git remote exists, so observed contexts and merge blocking remain unverified |
| 2026-08-05 | High-risk boundary | Approval requested | Bounded batches A–E document migration repair, ownership, auth lifecycle defaults, retention decisions, AI governance, non-goals, and required evidence; implementation remains pending explicit owner approval |
| 2026-08-05 | High-risk contract audit | Prepared | Independent read-only security, migration/data, and AI audits produced executable file/test contracts; corrected order is A → DATA-001 audit core → ownership/auth → lifecycle → AI, with legacy owner quarantine, authenticated material downloads, cascade-safe purge allowlist, tenant-safe retrieval, and admin-owned golden answers explicit |
| 2026-08-05 | High-risk boundary | Approved | Owner approved Batches A–E with every default in `REMAINING_HIGH_RISK_APPROVAL_PACKET.md`; golden-dataset content remains an explicit later owner/admin input |
| 2026-08-05 | CI-004 | Verification | Initial repair plus four explicit FK names passed both head upgrades, full downgrade to base, exact revision/table/enum assertions, eight initial runner unit tests, and guarded `_test` cleanup; later-revision edits awaited the documented narrow scope amendment approval |
| 2026-08-06 | Repository remote | Prepared | Configured `origin` as `https://github.com/duonggiang00/test-project.git`; read-only `ls-remote --heads` returned no heads, so the repository is reachable but still awaits its initial push |
| 2026-08-06 | CI-004 | Completed | Owner approved the narrow later-revision FK-name amendment; full PostgreSQL round trip, exact head/base schema assertions, import-environment regression coverage, single-head signature check, 40-unit fast suite, model/inventory gates, and final `_test` absence all pass |
| 2026-08-09 | DATA-001 | Completed | Added canonical correlated errors and BFF localization, privacy-allowlisted append-only audit core, exact audit schema/trigger verification, and hardened AI/UI error paths. Final fast passed in 94.6s; backend coverage is 77.50%, frontend 28.59%, changed executable coverage 83.84%; PostgreSQL integration passed 32 with two approved ownership XFAIL; migration round trip and real E2E 3/3 passed; migration, security, frontend, and completion reviews found no P1/P2. See `../handoffs/DATA-001.md`. |
| 2026-08-09 | DATA-006 | Completed | Recorded the owner-approved MVP retention policy in the canonical specification: no submission/grade purge, 30-day restricted raw AI payload retention, parent-lifetime redacted AI metadata, inherited chunk lifecycle, and no automatic audit-event purge. |
| 2026-08-09 | SEC-001/002, TEST-004, AI-005 | Completed | Added typed named permissions, explicit/derived teacher ownership, legacy-null quarantine, same-owner link enforcement, tenant-safe AI retrieval, atomic admin-override audit, retained-record/concurrency guards, and broad PostgreSQL negative matrices. Exact migration round trip, full backend/frontend gates, changed-code coverage, and independent reviews pass. |
| 2026-08-09 | SEC-006 | Review | Ownership/IDOR cases pass, but the approved matrix allows Admin student-submission actions while live self-service endpoints deliberately require a Student actor. An explicit on-behalf-of target/audit contract or matrix amendment is still required; SEC-003–005 also remain dependencies. |
| 2026-08-09 | DATA-009 | Partial | Pulled forward the separately approved access-contract slice: material storage is no longer anonymous or physically exposed, and owner/admin download is enforced. Soft-delete, restoration, 30-day lifecycle, and purge remain under DATA-003–005. |
| 2026-08-18 | DATA-003 | Completed | Added `SoftDeleteMixin`/default-exclusion listener for User/Topic/Exam/Question/StudyMaterial; migration `f9f952e6df1a` (revises `a83c1d7e9f02`); downgrade refuses while any row is soft-deleted; guarded round trip and full PostgreSQL integration (66/66) pass with no regressions. |
| 2026-08-18 | DATA-004 | Completed | Added owner/admin restore (`POST .../restore`) within the exact 30-day window shared with DATA-005's purge boundary; five-actor matrix and exact-boundary tests pass; every restore commits one `restore.performed` audit event atomically. PostgreSQL integration 86/86. |
| 2026-08-18 | DATA-002 | Completed | Registered and wired the remaining required audit actions (exam publish/unpublish/CRUD, topic/question/material CRUD, flashcard create, submission grading, user role-change/disable) onto their real call sites via a new `commit_with_audit` helper; `ai.*` events remain DATA-001/AI-003 scope. PostgreSQL integration 99/99. |
| 2026-08-18 | DATA-005 | Completed | Allowlisted, dry-run-capable purge for soft-deleted `StudyMaterial` only (User/Exam/Question/Topic/audit_events unreachable by construction); two-phase file quarantine; guarded `plan`/`apply`/`reconcile` CLI. PostgreSQL integration 108/108. |
| 2026-08-18 | DATA-009 | Completed | Closed the remaining lifecycle gap: removed a premature physical file delete at soft-delete time that broke the 30-day recovery window; full active→soft-deleted→restored/purged lifecycle proven cross-owner-indistinguishable throughout. PostgreSQL integration 112/112. |
| 2026-08-18 | Milestone 8 independent review | Completed | A separate reviewer agent read all five commits in full and ran both verification suites independently; no P1s found. Two P2 gaps closed before sign-off: (1) the submission/grade visibility guarantee through `AnalyticsService`/`HistoryService`/`StudentService.get_exam_result` rested on an undocumented, untested `exam_service`/`topic_service`/`question_service` guard — now documented and positively tested; (2) the change contract's required "recoverable job/receipt" for a crash mid-purge didn't exist — added a `purge_jobs` ledger (migration `1dfa8dca16d5`) and `reconcile` path. Final state: `node scripts/verify.mjs fast` green at every commit; full guarded PostgreSQL integration 115/115; guarded migration round trip clean through head `1dfa8dca16d5`. See `../handoffs/DATA-002-005-009.md`. |
| 2026-08-19 | AI-001 | Completed | Replaced two independently-instantiated OpenAI clients and three duplicated JSON extractors with one typed provider protocol, an OpenRouter adapter, per-use-case model policy from validated settings, and versioned prompt modules. A new non-baselined `provider-sdk-import` architecture rule keeps the SDK confined to the adapter. |
| 2026-08-19 | AI-002 / AI-009 | Completed | Added `AIGenerationJob` (migration `c4e1a70b58d9`) enforcing the §9.2 states through an allowlist with no `generated -> published` pair, an optimistic `version` column, and row locking. Removed the three `save-*` direct-write routes, closed both background-worker bypasses, and shipped the review UI plus the §10.3 "material upload and AI content generation with review" E2E flow. Two publish-path bugs were found and fixed by the tests themselves. `AIGradeSuggestion` establishes the advisory-grading invariant before any AI grading exists. |
| 2026-08-19 | AI-003 / AI-004 | Completed | Every transition and chat call now records the §2.4 metadata atomically with its state change; estimated cost is configuration-derived or an explicit null, never fabricated. Rendered prompts and raw output moved to `ai_restricted_payloads` (migration `e7b21c9d4a83`) under owner/admin-only access and §6.3's 30-day clock, expired through the existing purge path without loosening its allowlist. |
| 2026-08-19 | AI-006 / AI-007 / AI-008 | Deferred | Owner elected to defer the golden dataset, evaluation runner, and CI regression thresholds. AI-006 requires 30–50 admin-approved reference cases that no agent may invent or self-approve; AI-007 and AI-008 are blocked on it, and the change contract forbids inventing thresholds before an approved baseline exists. Hard safety invariants are enforced and tested regardless; AI *quality* is governed but not yet measured. |
| 2026-08-19 | Milestone 9 independent review | Completed | A separate reviewer agent read all eight commits and re-ran every suite. Two findings, both fixed before sign-off: a P1 auto-publish escape (the topic-kit background worker still wrote briefs and flashcard decks straight to live tables, producing no audit row on the owner path) and a P2 (the chat path recorded no §2.4 metadata and usually no audit event). Verified clean: publish reads only the reviewed draft, no `generated -> published` path exists, both redaction barriers hold under attack, restricted-payload cross-tenant reads are indistinguishable 404s, the purge allowlist did not loosen, and `GradingService` was untouched. Final: fast gate green, PostgreSQL integration 139/139, mocked E2E 24/24 across four browsers, migration round trip clean through `e7b21c9d4a83`. See `../handoffs/AI-001-004-009.md`. |
| 2026-08-20 | AI-RAG-HIDE-001 | Review | Owner approved a temporary default-off RAG/material-chat transition. The implementation preserves upload, extraction, chunks, generation, review, and historical RAG code/data while hiding chat and blocking both RAG routes. Focused backend/frontend tests, PostgreSQL integration, production build, and four-browser AI review E2E passed; Google Docs readback confirms the report contains none of the prohibited RAG/chat terms. Independent L3 review remains. See `AI-RAG-HIDE-001_CHANGE_CONTRACT.md` and `../handoffs/AI-RAG-HIDE-001.md`. |
| 2026-08-20 | EXAM-FLOW-QUICK-001 | Completed | Exposed Exam Builder in desktop/mobile navigation; Topic-backed `create=1` intent creates drafts and redirects to the Builder; direct creation and Topic-filtered bulk question assignment are connected; legacy response enums normalize to canonical uppercase form payloads. Frontend 121/121, guarded PostgreSQL exam/ownership 13/13, architecture guard, production build, and mocked E2E 28/28 across Chromium/Firefox/WebKit/mobile pass. Independent L2 review reconstructed and approved `2fe438f^..2fe438f` with no P1/P2/P3 findings. See `EXAM-FLOW-QUICK-001_CHANGE_CONTRACT.md` and `../handoffs/EXAM-FLOW-QUICK-001.md`. |
| 2026-08-20 | WORKSPACE-ARCHIVE-001 | Completed | Moved local report generation/output, its reconstructible commit snapshot, temporary/demo renders, unused brand experiments, obsolete pnpm/DeepEval state, and 12 unreferenced ad-hoc backend Python utilities into the ignored local archive. Active `backend/` now has zero loose `.py` files; 476 formal tests collect, scoped Ruff passes, and no executable reference targets an archived script. See `WORKSPACE-ARCHIVE-001_CHANGE_CONTRACT.md` and `../handoffs/WORKSPACE-ARCHIVE-001.md`. |
| 2026-08-24 | ANTI-NODB-001 / GUARD-008 | Completed | Replaced the remote icon font with Lucide, bundled IBM Plex Mono locally, extended CSS/design guard coverage, and reduced executable design-debt fingerprints from 328 to zero. Fast verification and 28/28 mocked tests across Chromium, Firefox, WebKit, and mobile Chrome pass without PostgreSQL. See `ANTI-NODB-001_CHANGE_CONTRACT.md` and `../handoffs/ANTI-NODB-001.md`. |
| 2026-08-25 | ANTI-PG-SEC-001 / SEC-003-007 | Completed | Removed all ten active query anti-patterns; implemented the approved access/refresh, revocation, CSRF, BFF, role-hydration, and student-only self-service contracts. Fast verification passed 487 tests plus production build; PostgreSQL integration passed 169/169; migration upgrade/downgrade/upgrade passed through head `a74c9d2e6f10`; real E2E passed 3/3; mocked E2E passed 28/28 across four browser projects; final independent review found no P1/P2; the managed `_test` database is absent. See `ANTI-PG-SEC-001_CHANGE_CONTRACT.md` and `../handoffs/ANTI-PG-SEC-001.md`. |
| 2026-08-25 | Workflow tracker reconciliation | Completed | Reconciled SEC-003–007 to `DONE` against commit `5cdb886`, its completed handoff, PostgreSQL/migration/E2E evidence, and independent review. Confirmed that the only remaining milestone work is five GitHub-hosted checks in `REVIEW`, one AI transition in `REVIEW`, and three owner-approved AI evaluation tasks in `DEFERRED`; EXAM-FLOW-QUICK-001 remains a supplemental L2 review item. |
| 2026-08-25 | CI-GITHUB-001 / CI-002/003/005/006/010 | Completed | Published and repaired the GitHub workflow; push run `32831201837` passed Fast, PostgreSQL integration/Alembic, and real E2E; PR run `32837826190` passed Fast, coverage, and 28/28 mocked browser tests. Applied `main` protection with the exact three strict required contexts and force-push/deletion denial; the earlier failed mocked check left PR #1 `unstable`, providing merge-block evidence. See `CI-GITHUB-001_CHANGE_CONTRACT.md` and `../handoffs/CI-GITHUB-001.md`. |
| 2026-08-25 | AI-RAG-ENABLE-001 | Completed | Owner reversed the temporary RAG suspension. Material chat is active by default; the synthetic compatibility processor remains default-disabled. Strict chat-role validation closes provider-priority injection, guarded PostgreSQL owner/student/inactive/admin and audit regression passes 3/3 with database cleanup, the capped live provider smoke completes, and the independent L3 reviewer reports no remaining P1/P2. No migration or data rewrite. See `AI-RAG-ENABLE-001_CHANGE_CONTRACT.md` and `../handoffs/AI-RAG-ENABLE-001.md`. |
| 2026-08-26 | TOOL-PYTEST-CACHE-001 / SEC-CSP-001 | Completed | Coverage is cache-independent and passes 352 unit/contract + 171 PostgreSQL + 149 frontend tests at 90.57%/61.25%; production and development HTTP CSP captures match the narrowed allowlists; fast passes 501 tests plus build; mocked E2E passes 28/28; independent L2 review found no P1/P2 and both P3 documentation findings were closed. See `WORKFLOW-COVERAGE-CSP-001_CHANGE_CONTRACT.md` and `../handoffs/WORKFLOW-COVERAGE-CSP-001.md`. |
| 2026-08-26 | UI-LANGUAGE-001 / TEST-FE-COVERAGE-001 | Completed | Translated all 37 identified executable frontend files across public/auth, admin/AI, exam, and student/shared surfaces; zero unintended Vietnamese source matches remain. Independent-review findings were remediated: faithful product claims, named pagination controls, global coverage 76.97%, changed-line coverage 82.14%, Windows/Linux visual evidence, and an unobscured AI guardrail. Canonical fast passed and final independent review approved with no remaining P1/P2/P3 findings. See `../handoffs/FRONTEND-ENGLISH-COVERAGE-001.md`. |
| 2026-08-27 | WORKFLOW-TOKEN-001 / TOK-001-005 | Completed | Progressive-disclosure rules, live bounded context, compact/redacted verification evidence, conservative resume, model routing, and six fixed scenarios are implemented. Focused script tests pass 22/22; fast passes 534 tests plus build with the complete 182-test frontend Jest project executed once; exact resume reuses 13/13 safe steps; median L0-L2 context reduction is 79.71% and compact success stdout falls 49.60%. Final independent L2 review found no P1/P2/P3. See `WORKFLOW-TOKEN-001_CHANGE_CONTRACT.md` and `../handoffs/WORKFLOW-TOKEN-001.md`. |
| 2026-08-27 | AI-006 dataset validator | Blocked | Implemented the versioned strict JSONL contract, Ed25519 approval verification rooted in an externally pinned owner fingerprint, recursive secret screening, sanitized file failures, canonical fingerprint, approved 40-case distribution check, and partial-review mode. Focused tests pass 28/28, canonical fast passes 562 tests plus build, and final independent L3 review reports no P1/P2/P3. No trusted owner key, protected trust-root fingerprint, or approved dataset file was added. AI-006 remains blocked until owner/admin supplies and pins the key and signs all 40 cases; AI-007/008 and RAG-SEMANTIC-001 remain downstream. See `../handoffs/AI-006-DATASET-VALIDATOR.md`. |

## 18. Known program risks

| Risk | Mitigation |
|---|---|
| Existing rules contradict each other | Mitigated by completed Milestone 1 and the canonical root/scoped rule hierarchy |
| Historical Antigravity rules could contaminate agent discovery | Mitigated: the full legacy tree is recoverable under ignored `.legacy-archive/antigravity-agents-20260805`; active `.agents` contains only three validated skills |
| Broad ignore rules could silently exclude test suites | Mitigated by CI-001; retain `git check-ignore` validation in future CI work |
| Backend integration tests could mutate a developer database | Mitigated: direct integration fixtures require `ENV=test`; the runner manages only a new local `_test` database and refuses unsafe or pre-existing targets |
| Backend tests share a global SlowAPI limiter and exceed auth limits during a full run | Mitigated with per-test limiter reset; the latest canonical fast and PostgreSQL integration gates pass |
| CI workflow has not executed on GitHub | Mitigated: hosted push and PR runs are green, `main` has the declared strict required contexts, and PR #1 demonstrated the blocked state while a required check failed |
| Legacy Alembic history could not round trip | Mitigated by separately approved explicit FK names and CI-004's exact-schema guarded PostgreSQL upgrade/downgrade/upgrade gate |
| Frontend coverage was historically too low | Mitigated: the honest all-source baseline is now 76.97% (`10,588/13,756` lines), CI forbids regression, and changed executable lines pass the unchanged 80% target at 82.14% |
| Administrative on-behalf-of student submission is not implemented | The approved current contract keeps self-service routes student-only and uses separate audited Admin management operations; any future impersonation/on-behalf-of workflow requires a new approved target and audit contract |
| AI output is governed but its quality is not yet measured | Hard safety invariants (no cross-owner retrieval, no automatic publication, no final AI grading) are enforced in code and tested. Correctness, groundedness, injection resistance, latency, and cost remain unmeasured until AI-006–008 are completed; do not represent Milestone 9 as making AI output good, only as making it reviewable |
| `AIGradeSuggestion` has no production caller | The advisory invariant currently holds trivially because nothing generates a suggestion yet. When AI grading is implemented, the apply-on-approval path described in the model docstring still has to be built and tested |
| Post-MVP submission/grade retention remains undecided | The approved MVP policy forbids permanent purge; require a later educational-record ADR and explicit owner approval before changing it |
