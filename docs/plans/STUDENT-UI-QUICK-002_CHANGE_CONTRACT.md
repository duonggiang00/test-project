# Change Contract: STUDENT-UI-QUICK-002 Student correctness and usability repair

Risk level: L2
Owner: Codex
Approval required: No additional approval; the project owner explicitly requested the quick repair in the active task.
Approval evidence: User request on 2026-08-20.

## Scope
- In scope:
  - Make the backend-provided exam timer authoritative across resume and refresh.
  - Warn before leaving an in-progress exam and prevent answer changes from resetting the countdown interval.
  - Return real Topic, question-count, maximum-score, and remaining-time metadata to Student consumers.
  - Count unanswered questions in the result presentation without fabricating persisted answers.
  - Make profile statistics request the maximum supported page, normalize percentages, and label the summary as partial when more pages exist.
  - Repair keyboard semantics for flashcard flipping and matching interactions.
  - Synchronize the Student Playwright page object with the current UI.
- Out of scope:
  - Database migrations, authentication, permissions, ownership, grading policy, and autosave persistence.
  - A full visual redesign or new notification infrastructure.

## Behavior
- Before:
  - Resuming an exam restarts the visible timer while the backend retains the original start time.
  - Answer changes recreate the countdown interval; exit and refresh can discard local answers without warning.
  - Exam cards rely on optional metadata absent from the backend response.
  - Unanswered questions disappear from result counts/details.
  - Profile statistics cover only the first four exams and average raw scores.
  - Flashcard and matching surfaces depend on pointer-only `div` interactions.
- After:
  - The start response includes remaining seconds calculated from the persisted submission start time.
  - The timer uses one deadline and current-answer refs; leaving an answered exam requires confirmation.
  - Student list responses provide verified Topic, question count, and maximum score.
  - Results include an explicit zero-point entry for each unanswered exam question.
  - Profile statistics load up to 100 exams, average normalized percentages, and explicitly label partial summaries.
  - Flashcard and matching actions are keyboard-operable native buttons.
- Preserved invariants:
  - Existing endpoints, request payloads, grading behavior, BFF routing, and backend authorization remain unchanged.
  - Added response fields are non-breaking and contain no answer keys.

## Expected files and contracts
- Files/modules: Student schemas/service/tests; Student types/hooks/pages/components/tests/POM.
- API/event/schema impact: Non-breaking response additions to Student exam list/start contracts.
- Migration/data impact: None.
- Security/ownership/tenant impact: None; existing visibility statements remain authoritative.

## Verification contract
- Targeted tests: Student start/list/result backend contracts; timer/leave behavior; profile statistics; flashcard/matching keyboard behavior.
- Static/type checks: Scoped Ruff, mypy where configured, frontend ESLint, architecture guard.
- Integration/PostgreSQL checks: Existing Student PostgreSQL/ownership suite when available; no new database behavior.
- Build/E2E/visual checks: Frontend production build and affected Student E2E contract/POM check.
- Manual verification: Resume timer, leave confirmation, card metadata, unanswered result, profile summary, keyboard controls.

## Rollback
- Code rollback: Revert the files listed in the handoff for this task.
- Data rollback: Not applicable.

## Assumptions and drift
- Verified assumptions:
  - `Submission.start_time` is the backend source of truth and submit already enforces it.
  - FastAPI pagination accepts the requested size of 100 within its configured maximum.
  - The Student exam list currently omits Topic, question-count, and maximum-score metadata.
- Unresolved assumptions:
  - Browser autosave requires a separate product contract and is not part of this repair.
- SPEC_DRIFT:
  - Several untouched Student styles and the global remote icon font still violate the strict black-and-white/local-font decision; visual normalization remains separate from this correctness repair.
  - The existing start-exam contract exposes raw `metadata_json`; some question formats may store answer-bearing matching or fill-in-blank metadata there. This pre-existing security-sensitive contract requires a separately approved L3 remediation and is not broadened by this task.
