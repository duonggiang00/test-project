# Handoff: STUDENT-UI-QUICK-002 Student correctness and usability repair

Status: REVIEW
Risk level: L2

## Outcome
- Summary: Student exam resume now uses backend-authoritative remaining time, answer changes no longer recreate the timer, answered exams warn before navigation loss, Student cards receive real metadata, results count unanswered questions, profile scores are normalized, and flashcard/matching interactions use native buttons.
- Requirements/task IDs: `STUDENT-UI-QUICK-002`

## Files changed
- `backend/app/schemas/student.py` — add non-breaking Student list/start metadata and a result-only option schema.
- `backend/app/services/student_service.py` — derive remaining time and list metadata; include unanswered questions in result output.
- `backend/tests/test_student.py` — cover remaining time, metadata, unanswered results, and result-only answer keys.
- `frontend/src/types/index.ts` — consume the additive response fields.
- `frontend/src/app/student/exam/[id]/page.tsx` — use a deadline-based timer and protect local answers before exit/reload.
- `frontend/src/app/student/profile/page.tsx` — normalize scores and label partial summaries.
- `frontend/src/app/student/topics/[id]/decks/[deck_id]/study/page.tsx` — make card reveal keyboard-operable and monochrome.
- `frontend/src/components/features/student-home/FeaturedExamCard.tsx` — display score against the verified maximum.
- `frontend/src/components/features/student-home/FeaturedExamList.tsx` — pass verified metadata to cards.
- `frontend/src/components/features/student/BrutalistMatchingUI.tsx` — use native pressed-state buttons and stabilize the default match collection.
- `frontend/src/components/features/student/ExamResultView.tsx` — distinguish unanswered questions and consume result-only correct options.
- `frontend/src/components/features/student/StudentHeader.tsx` — reduce mobile width and normalize touched monochrome states.
- `frontend/tests/component/student-exam-errors.test.tsx` — cover backend remaining time and exit confirmation.
- `frontend/tests/component/student-flashcard-accessibility.test.tsx` — cover native card/matching controls.
- `frontend/tests/component/student-profile-summary.test.tsx` — cover normalized statistics.
- `frontend/tests/pom/StudentExamPage.ts` — synchronize exam and matching locators with the live UI.
- `docs/generated/openapi.json` — regenerate the reviewed additive API contract.
- `docs/generated/project-inventory.json` — regenerate the current technical inventory.

## Verification
| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| Guarded PostgreSQL `tests/test_student.py` | 0 | 5 | 5 | 0 | 0 | Test DB created and dropped; start/list/submit/result contracts passed. |
| Backend API contract suite | 0 | 18 | 18 | 0 | 0 | `VERIFY_OK mode=contract`. |
| Scoped Ruff | 0 | N/A | N/A | 0 | 0 | All checks passed. |
| Configured mypy gate | 0 | 22 files | 22 files | 0 | 0 | `Success: no issues found`. |
| Full frontend Jest | 0 | 128 | 128 | 0 | 0 | 27 suites passed. |
| Scoped frontend ESLint | 0 | N/A | N/A | 0 | 0 | No findings. |
| Frontend production build | 0 | 20 pages | 20 pages | 0 | 0 | Compile, TypeScript, static generation, and trace collection passed. |
| Architecture guard | 0 | 123 | 123 | 0 | 0 | `ARCHITECTURE_OK current=123 baseline=150`. |
| OpenAPI generate/check | 0 | 60 paths | 60 paths | 0 | 0 | Generated contract matches live API. |
| Inventory generate/check | 0 | 370 files | 370 files | 0 | 0 | Source-tree hash is current. |
| Playwright real-suite discovery | 0 | 3 | 3 | 0 | 0 | Setup plus Chromium Student flow parse successfully. |
| `git diff --check` | 0 | N/A | N/A | 0 | 0 | No whitespace errors; unrelated CRLF warnings only. |

## Impact
- API/event/schema contract: Additive Student response fields only; no request or endpoint removal. Correct-answer flags are available only from the post-submission result response.
- Migration/data: None.
- Security/ownership/tenant: Existing Student visibility queries and role enforcement are unchanged.
- Dependency/toolchain: None.

## Manual evidence
- Scenario: Static route/component review plus executable component coverage for resume timer, leave confirmation, flashcard reveal, matching selection, and profile score normalization.
- Result: Expected state transitions and accessible roles are covered; full browser execution was not performed.
- Screenshot/trace: Not collected in this quick repair.

## Risks and follow-up
- Known risks: The existing start-exam response still exposes raw `metadata_json`; answer-bearing matching/fill-in-blank metadata needs a separately approved L3 contract redesign. Student visual surfaces still contain legacy gray/semantic colors and the application still loads Material Symbols remotely.
- Unverified items: Real-server Student E2E and multi-browser/mobile visual regression were not executed. An explicit out-of-config mypy probe of the legacy `student_service.py` reports five existing SQLAlchemy `Column[...]` typing errors; the configured 22-file gate passes.
- Follow-up tasks: Approve and implement the question-metadata security contract, run isolated real E2E, add due-review summaries, and complete the strict black-and-white/local-icon cleanup.

## Rollback
- Code: Revert the files listed above for `STUDENT-UI-QUICK-002` only.
- Data: No rollback is required.
