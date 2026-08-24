# Change Contract: STUDENT-UI-QUICK-001 — Student flow repair

Risk level: L2
Owner: Codex
Approval required: No additional approval; the project owner explicitly requested the Student UI adjustment.
Approval evidence: User request in the active task on 2026-08-20.

## Scope

- In scope:
  - Make published/in-progress/completed exams discoverable from the active Student UI.
  - Repair dead Student navigation and use one canonical exam-taking/result path.
  - Preserve loaded profile values when entering edit mode.
  - Keep the touched surfaces square, high-contrast, responsive, and keyboard-operable.
- Out of scope:
  - Backend, database, authentication lifecycle, permissions, and ownership changes.
  - New reminders, badges, missions, help, or material-download capabilities.
  - A full redesign of every legacy Student component.

## Behavior

- Before:
  - Student Home shows topics but does not render the existing exam list.
  - the exam exit action targets a non-existent `/student/topics` route.
  - both `/student/exam/<id>` and `/student/exams/<id>` expose different exam UIs.
  - the profile edit draft may be initialized before SWR supplies the profile.
- After:
  - Student Home exposes both available exams and the Topic library.
  - Topic exam actions distinguish start, continue, and result states.
  - active and compatibility links converge on `/student/exam/<id>` and its result route.
  - profile editing always starts from the latest loaded profile.
- Preserved invariants:
  - Backend remains authoritative for visibility and access.
  - Existing API payloads and BFF transport remain unchanged.
  - Flashcard review and exam submission behavior remain unchanged.

## Expected files and contracts

- Files/modules: Student routes, Student home/topic/profile components, focused frontend tests.
- API/event/schema impact: None.
- Migration/data impact: None.
- Security/ownership/tenant impact: None; frontend changes do not broaden access.

## Verification contract

- Targeted tests: Student home, topic exam actions, profile edit initialization, existing Student exam errors.
- Static/type checks: Frontend ESLint.
- Integration/PostgreSQL checks: Not required; no backend or persistence change.
- Build/E2E/visual checks: Production build and affected Student E2E when the local environment supports them.
- Manual verification: Home → Topic/Exam → Result and Home → Profile at desktop/mobile widths.

## Rollback

- Code rollback: Revert the scoped Student UI files and this contract.
- Data rollback: Not applicable.

## Assumptions and drift

- Verified assumptions:
  - `/student/exam/<id>` is the route linked from the active Topic page.
  - Student Home currently omits the existing `FeaturedExamList` component.
  - Student profile and exam APIs already exist.
- Unresolved assumptions:
  - Visual regression baselines may require a separate reviewed update.
- SPEC_DRIFT:
  - Existing Student surfaces still contain gray/colored states and a remote icon font despite the canonical black-white/local-font rule; this quick repair does not authorize a whole-application restyle.
