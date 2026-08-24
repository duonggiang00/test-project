# Change Contract: EXAM-FLOW-QUICK-001 — Expose exam creation and question assignment

Risk level: L2 — cross-route user flow using existing public contracts  
Owner: Codex  
Approval required: Yes  
Approval evidence: The project owner approved the complete implementation plan in this thread on 2026-08-20.

## Scope

- In scope:
  - Make the existing Exam Builder reachable from desktop and mobile teacher/admin navigation.
  - Carry Topic create intent into the exam list through URL-backed query state.
  - Create new exams as drafts and redirect directly to their existing builder.
  - Make direct question creation and bulk assignment discoverable and reliable.
  - Emit canonical uppercase question type and difficulty values from both authoring forms.
- Out of scope:
  - Backend endpoint, OpenAPI, database, ownership, permission, audit, or publishing-contract changes.
  - A new multi-step wizard, new exam/question schema, or question-sharing semantics.
  - RAG/report work already present in the shared worktree.

## Behavior

- Before:
  - `/exams` and `/exams/{id}` implement creation and assignment, but the primary sidebar has no Exam entry.
  - Topic `Create Exam` opens only the list and neither opens the form nor preserves its Topic as the creation context.
  - The authoring forms can emit legacy lowercase difficulty/type values rejected by the backend enums.
- After:
  - Teacher/admin users can enter Exam Builder from desktop navigation and a mobile header shortcut.
  - `/exams?topic_id=<uuid>&create=1` opens the draft form once with the Topic selected; cancel removes only the create intent.
  - Successful creation always sends `is_published=false` and navigates to `/exams/{id}`.
  - Exam Builder defaults its bank filter to the exam Topic, hides questions already in that exam, and refreshes both server-state views after bulk assignment.
  - New form submissions emit only canonical uppercase question type and difficulty values.
- Preserved invariants:
  - Browser requests continue through the Next.js BFF client and existing service functions.
  - Backend permission and ownership checks remain authoritative.
  - Existing edit/publish behavior and every API payload shape remain compatible.

## Expected files and contracts

- Files/modules:
  - Admin navigation/layout, Topic detail, Exam list/detail, Question Bank, and focused frontend tests.
  - Optimization tracker and engineering handoff.
- API/event/schema impact: None. Existing endpoints and payload shapes are reused.
- Migration/data impact: None.
- Security/ownership/tenant impact: None; existing backend enforcement is unchanged.

## Verification contract

- Targeted tests:
  - Navigation reachability, query-backed create intent, draft payload/redirect, safe failure, canonical enums, and bulk assignment state transitions.
- Static/type checks: Scoped ESLint and production TypeScript build.
- Integration/PostgreSQL checks: Existing exam and ownership suites against the guarded PostgreSQL runner.
- Build/E2E/visual checks:
  - Production build.
  - Mocked teacher journey from dashboard/topic through draft creation and both question paths on Chromium, Firefox, WebKit, and mobile Chrome.
  - Desktop/mobile screenshot or trace for the changed screens.
- Manual verification: Confirm no manual URL entry is required and no lowercase enum leaves either authoring form.

## Rollback

- Code rollback: Revert the navigation/query/form/test changes; existing backend routes and persisted data remain valid.
- Data rollback: None.

## Assumptions and drift

- Verified assumptions:
  - `POST /exams`, `POST /exams/{id}/questions`, and `POST /exams/{id}/questions/bulk` already enforce the required backend policies.
  - Current E2E coverage reaches `/exams` directly, which masks the missing product navigation.
  - Question and difficulty enums are uppercase in the backend.
- Unresolved assumptions: None.
- SPEC_DRIFT:
  - The canonical critical flow requires teacher exam creation, but the active navigation does not expose the implemented route. This task repairs presentation and routing without changing the contract.
