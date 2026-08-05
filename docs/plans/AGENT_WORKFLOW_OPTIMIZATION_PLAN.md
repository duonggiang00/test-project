# Agent Workflow Optimization Plan

Status: Active  
Plan owner: Project owner  
Execution owner: Primary coding agent  
Created: 2026-08-05  
Last updated: 2026-08-05  
Canonical specification: [`../spec/CANONICAL_PROJECT_SPEC.md`](../spec/CANONICAL_PROJECT_SPEC.md)

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
```

Milestones 1 and 2 may partially overlap. Feature development may resume under the new workflow after Milestone 3, while later hardening milestones continue.

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

Exit criteria:

- A clean Windows checkout can install and run fast verification.
- Local and CI use the same logical entry points.

## 7. Milestone 3 — Effective CI gates

Goal: Prevent unverified code from entering `main`.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| CI-001 | Fix `.gitignore` so backend and frontend test suites are tracked | DONE | PLAN-003 | `git check-ignore` confirms test files are not ignored |
| CI-002 | Add pull-request fast gate | REVIEW | TOOL-006, CI-001 | Workflow implementation and 178.9s local gate pass are verified; awaiting the first GitHub pull-request run |
| CI-003 | Add push-to-main integration gate | REVIEW | TOOL-006, TOOL-008, CI-001 | Workflow implementation, pgvector service profile, 24/24 local integration pass, and cleanup are verified; awaiting the first push-to-`main` run |
| CI-004 | Add Alembic upgrade/downgrade/upgrade verification | BLOCKED | CI-003 | Runner and CI step are implemented, but initial upgrade fails in `27f1dff6a48f` when dropping nonexistent `ix_user_email`; migration edit requires owner approval |
| CI-005 | Add mocked Playwright critical-flow suite to PRs | REVIEW | CI-002 | Backend-independent admin flow passes four local projects in 52s with failure artifacts; awaiting first GitHub pull-request run |
| CI-006 | Add real-backend/PostgreSQL smoke E2E suite on `main` | REVIEW | CI-003, CI-005 | Guarded runner passed login, topic/exam/question creation, student submit/result, cleanup, and 3/3 owner/flake policy locally in 32s; awaiting first GitHub `main` run |
| CI-007 | Add Chromium, Firefox, WebKit, and mobile projects | DONE | CI-005, CI-006 | Chromium, Firefox, WebKit, and Pixel 7 Chrome matrix passes locally in 52s, within the 10-minute budget |
| CI-008 | Upload logs, traces, screenshots, and reports on failure | DONE | CI-005 | Local failures produced error context/screenshot/video; config captures first-retry trace and CI uploads the complete Playwright report tree |
| CI-009 | Add flaky-test retry/ownership policy | DONE | CI-005 | One retry collects diagnostics; report checker fails retried/flaky/unowned tests and the synthetic violation fixture fails as expected |
| CI-010 | Protect required checks before merge | REVIEW | CI-002–009 | Machine-readable policy and drift gate identify three PR requirements; remote application and merge-block evidence await the first GitHub PR |

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
| TEST-004 | Add ownership and tenant-isolation negative-test matrix | BLOCKED | TEST-003, GOV-002 | Exam update covers all five actors, but strict expected failures confirm missing non-owner enforcement for bulk assignment and material detail; fixes require approved SEC-001/002 work |
| TEST-005 | Expand query-budget tests for important list/detail endpoints | DONE | TEST-003 | PostgreSQL regression compares exam detail with 2 vs 10 nested questions; both stay within four queries and the larger result does not add queries |
| TEST-006 | Separate frontend unit, component, mocked E2E, and real E2E suites | DONE | CI-005, CI-006 | Unit, component, mocked four-browser, and guarded real-backend suites have explicit commands; all four tiers pass independently |
| TEST-007 | Add hydration, cache-mutation, and BFF-only tests | DONE | TEST-006 | Five frontend unit suites pass 13 tests including Zustand no-token hydration, SWR non-revalidating cache mutation, and BFF cookie/path/host/redirect contracts |
| TEST-008 | Add brutalist visual regression coverage | DONE | TEST-006, CI-007 | Reviewed black/white desktop/mobile baselines exist for all four browser projects; tooling overlay removed and clean matrix passes 4/4 |
| TEST-009 | Cover loading, empty, error, disabled, and keyboard states | DONE | TEST-006 | Five component tests cover loading/error/empty/disabled/focus semantics and mocked flow proves keyboard activation across four browser projects |

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
| GUARD-008 | Enforce local font and black/white design-token policy | DONE | GOV-006 | Remote-font, named-color, and non-monochrome literal fixtures are detected; 122 current color-debt fingerprints cannot increase |
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
| SEC-001 | Implement named permission-policy layer | TODO | GOV-002, TEST-004 | Current admin/teacher parity maps through policies, not scattered role checks |
| SEC-002 | Define and apply ownership fields and filters to sensitive resources | TODO | SEC-001 | Non-owner teacher access is rejected by backend |
| SEC-003 | Implement access/refresh token lifecycle and rotation | TODO | GOV-001, TEST-003 | Rotation, expiry, and replay cases pass |
| SEC-004 | Implement revocation and logout semantics | TODO | SEC-003 | Single/all-session behavior is tested and audited |
| SEC-005 | Implement CSRF protections for cookie-authenticated mutations | TODO | SEC-003 | Cross-site mutation tests fail safely |
| SEC-006 | Add IDOR and cross-tenant regression suite | TODO | SEC-002–005 | Identifier probing cannot cross ownership boundaries |
| SEC-007 | Verify canonical role redirects and frontend UX guards | TODO | SEC-001, TEST-006 | `/dashboard`, `/student/home`, and `/login` behavior passes |

Exit criteria:

- Backend ownership enforcement is complete for scoped resources.
- Auth lifecycle and cross-tenant negative tests pass.

## 12. Milestone 8 — Audit, soft delete, and upload governance

Goal: Make sensitive actions traceable and deleted data recoverable for 30 days.

Migration tasks require owner approval and downgrade evidence.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| DATA-001 | Implement canonical audit-event model/service | TODO | GOV-003, CI-004 | Migration round trip and audit schema tests pass |
| DATA-002 | Instrument admin/teacher, exam, grading, AI, restore, purge, and auth events | TODO | DATA-001 | Required actions produce redacted audit events |
| DATA-003 | Implement reusable soft-delete fields and query policy | TODO | GOV-002, CI-004 | Default reads exclude deleted rows |
| DATA-004 | Implement admin/owner restoration policy | TODO | DATA-003, SEC-002 | Authorization and 30-day eligibility tests pass |
| DATA-005 | Implement 30-day purge service with dry run and audit | TODO | DATA-002–004 | Boundary-time, dry-run, purge, and rollback tests pass |
| DATA-006 | Confirm separate retention for submissions, grades, and sensitive AI logs | TODO | DATA-001 | Owner-approved policy is recorded before permanent purge |
| DATA-007 | Introduce local storage interface for uploaded files | DONE | GOV-001 | Injected `FileStorage` protocol preserves local behavior with atomic, UUID-named writes and root-confined deletion; fast and PostgreSQL gates pass |
| DATA-008 | Enforce PDF/DOCX/PPTX/TXT and 50 MB validation | DONE | DATA-007 | 17 focused cases cover extension, MIME, PDF/OOXML signature, UTF-8 text, size, collision, atomic-failure cleanup, DB rollback, and path boundaries; endpoint reads at most 50 MB + 1 byte |
| DATA-009 | Apply owner/admin authorization and 30-day lifecycle to files | TODO | DATA-003–005, DATA-007 | Cross-owner access and restore/purge tests pass |

Exit criteria:

- Required actions are auditable.
- Applicable deleted data is recoverable for 30 days.
- File handling matches the approved contract.

## 13. Milestone 9 — AI reliability and evaluation

Goal: Ensure AI output is reviewable, tenant-safe, measurable, and regression-tested.

| ID | Task | Status | Depends on | Acceptance evidence |
|---|---|---|---|---|
| AI-001 | Introduce provider abstraction and use-case model policy | TODO | GOV-001 | Provider/model can change through configuration |
| AI-002 | Implement generation and approval state machine | TODO | DATA-001 | No generated content can bypass `awaiting_review` |
| AI-003 | Implement prompt versioning and AI audit metadata | TODO | AI-001, DATA-001 | Prompt/model/tokens/cost/latency/context are traceable |
| AI-004 | Add redaction and access controls for sensitive AI logs | TODO | AI-003, SEC-002 | Sensitive content is protected and tested |
| AI-005 | Enforce tenant-safe retrieval | TODO | SEC-002, TEST-004 | Cross-owner documents never enter retrieval context |
| AI-006 | Build the first admin-approved golden dataset | TODO | AI-001 | 30–50 reviewed cases cover critical AI use cases |
| AI-007 | Implement correctness, groundedness, citation, relevance, injection, latency, and cost evals | TODO | AI-006 | Repeatable evaluation report is produced |
| AI-008 | Add prompt/model regression thresholds to CI | TODO | AI-007 | Material metric regressions block the governed change |
| AI-009 | Verify AI grading remains advisory until teacher/admin approval | TODO | AI-002, AI-007 | State and authorization tests prevent automatic final grading |

Exit criteria:

- AI changes are measurable and auditable.
- Sensitive retrieval is tenant-isolated.
- All AI-generated publishable content requires human approval.

## 14. Agent assignment model

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

## 15. Definition of Done

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

## 16. Current progress log

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

## 17. Known program risks

| Risk | Mitigation |
|---|---|
| Existing rules contradict each other | Mitigated by completed Milestone 1 and the canonical root/scoped rule hierarchy |
| Historical Antigravity rules could contaminate agent discovery | Mitigated: the full legacy tree is recoverable under ignored `.legacy-archive/antigravity-agents-20260805`; active `.agents` contains only three validated skills |
| Broad ignore rules could silently exclude test suites | Mitigated by CI-001; retain `git check-ignore` validation in future CI work |
| Backend integration tests could mutate a developer database | Mitigated: direct integration fixtures require `ENV=test`; the runner manages only a new local `_test` database and refuses unsafe or pre-existing targets |
| Backend tests share a global SlowAPI limiter and exceed auth limits during a full run | Mitigated with per-test limiter reset; current full baseline is 29 passed in 23.78s |
| CI workflow has not executed on GitHub | CI-002/003 implementation is in REVIEW; create the initial commit and configure a remote before relying on required-check status |
| Alembic cannot build a fresh database | CI-004 blocks at initial migration `27f1dff6a48f`; obtain owner approval before correcting migration history, then rerun upgrade/downgrade/upgrade |
| Frontend coverage baseline is only 0.75% | Baseline instruments all `frontend/src` instead of hiding unimported files; forbid regression and raise it through TEST-006–009 with ~80% coverage on changed executable lines |
| Current code may not yet satisfy target ownership separation | Preserve current behavior through policies, then harden under Milestone 7 |
| Submission/grade purge policy is not approved | Block permanent purge for these records until DATA-006 |
