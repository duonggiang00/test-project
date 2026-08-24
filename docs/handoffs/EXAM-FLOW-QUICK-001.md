# Handoff: EXAM-FLOW-QUICK-001 — Expose exam creation and question assignment

Status: REVIEW  
Risk level: L2

## Outcome

- Summary: Teacher/admin users can discover Exam Builder from desktop and mobile, start a Topic-backed draft, enter the existing Builder, create a question directly, or bulk-assign Topic questions without manually entering a URL. New and legacy-loaded forms submit only canonical uppercase question enums.
- Requirements/task IDs: `EXAM-FLOW-QUICK-001`

## Files changed

- `docs/plans/EXAM-FLOW-QUICK-001_CHANGE_CONTRACT.md` — approved scope, behavior, verification, and rollback contract.
- `frontend/src/components/features/admin/Sidebar.tsx` — desktop Exam Builder entry.
- `frontend/src/app/(admin)/layout.tsx` — mobile Exam Builder shortcut.
- `frontend/src/app/(admin)/topics/[id]/page.tsx` — Topic-backed create intent URL.
- `frontend/src/app/(admin)/exams/page.tsx` — query-backed draft form, one-time cancel semantics, draft-only create payload, and Builder redirect.
- `frontend/src/app/(admin)/exams/[id]/page.tsx` — Topic-default Question Bank, assigned-question exclusion, bulk refresh, and canonical question payloads.
- `frontend/src/app/(admin)/questions/page.tsx` — canonical standalone Question Bank payloads.
- `frontend/src/lib/questionEnums.ts` — legacy-read/canonical-write enum normalization.
- `frontend/tests/component/exam-creation-flow.test.tsx` — navigation, query intent, draft payload, redirect, cancel, and safe-error coverage.
- `frontend/tests/component/exam-builder-flow.test.tsx` — bank filtering/assignment, cache refresh, canonical enum, and legacy normalization coverage.
- `frontend/tests/e2e/admin-flow.spec.ts` — discoverable desktop/mobile journey through draft creation and both question paths.
- `frontend/tests/e2e/student-flow.spec.ts` — real-flow setup now publishes only after questions are added.
- `frontend/tests/pom/AdminDashboardPage.ts` — draft creation and explicit publish helpers.
- `frontend/tests/e2e/admin-flow.spec.ts-snapshots/*.png` — reviewed desktop/mobile modal, Builder, and sidebar baselines.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — REVIEW progress evidence.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| Focused Jest: `exam-creation-flow` + `exam-builder-flow` | 0 | 9 | 9 | 0 | 0 | Query intent, draft, safe failure, assignment, and enum contracts pass |
| Full frontend Jest (`jest --runInBand`) | 0 | 121 | 121 | 0 | 0 | 24 suites pass |
| Scoped ESLint over implementation/tests | 0 | — | — | 0 | — | No findings |
| `node scripts/architecture-guard.mjs check` | 0 | 150 | 150 | 0 | 0 | `ARCHITECTURE_OK current=150 baseline=150` |
| Frontend `next build --webpack` | 0 | 20 routes | 20 | 0 | 0 | Compile, TypeScript, static generation, and build traces pass |
| Guarded PostgreSQL exam/ownership regression | 0 | 13 | 13 | 0 | 0 | Test database created and dropped in `finally` |
| Full mocked Playwright E2E | 0 | 28 | 28 | 0 | 0 | Chromium, Firefox, WebKit, and Pixel 7 Chrome pass |
| Playwright result policy | 0 | 28 | 28 | 0 | 0 | `PLAYWRIGHT_POLICY_OK tests=28` |

The first sandboxed browser attempt could not spawn browser executables (`EPERM`). The same suite was rerun with browser-launch permission and passed; this was an execution sandbox limitation, not an application failure.

## Impact

- API/event/schema contract: No backend or OpenAPI changes. Reuses `POST /exams`, `POST /exams/{exam_id}/questions`, and `POST /exams/{exam_id}/questions/bulk`. Adds only the frontend query contract `topic_id` plus `create=1`.
- Migration/data: None.
- Security/ownership/tenant: None; backend remains authoritative for every operation.
- Dependency/toolchain: None.

## Manual evidence

- Scenario: Starting at Dashboard, desktop navigates through Topic Hub and Topic Exams; mobile uses the visible `EXAMS` shortcut. Both create a draft, arrive at the Builder, add a direct question, then select and bulk-assign a bank question.
- Result: Both questions appear in the exam; the draft payload contains `is_published=false`; no manual `/exams` entry is needed; mobile has no horizontal overflow.
- Screenshot/trace: `frontend/tests/e2e/admin-flow.spec.ts-snapshots/exam-create-draft-*.png`, `exam-builder-empty-*.png`, and updated `topics-page-*.png`. The pass run produced no retry trace because no retry was needed.

## Risks and follow-up

- Known risks: Admin and Teacher still intentionally share the same presentation; backend ownership/permission policy remains the only authority.
- Unverified items: Independent L2 diff review has not yet been recorded, so status remains `REVIEW` rather than `DONE`.
- Follow-up tasks: Independent reviewer should inspect only the scoped EXAM-FLOW diff and either sign off or return concrete findings.

## Rollback

- Code: Revert the scoped navigation, query-state, form, normalization, POM/E2E, and snapshot changes listed above.
- Data: None; no migration or data rewrite occurred.
