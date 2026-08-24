# Change Contract: STUDENT-EXAM-QUESTION-001 Safe question interaction repair

Risk level: L3
Owner: Codex
Approval required: Yes
Approval evidence: On 2026-08-21, after reviewing screenshots and the identified answer-key exposure, the project owner explicitly requested implementation with “tiến hành sửa lỗi”.

## Scope
- In scope:
  - Render fill-in-blank inputs for both the canonical `[BLANK]` token and legacy `___` content.
  - Require future AI-generated fill-in-blank content to use `[BLANK]` and advance the prompt version.
  - Replace the unstable matching layout with equal-width vertical columns on desktop and a readable matched-pair summary on mobile.
  - Preserve keyboard interaction, visible focus, strict black/white styling, and current answer submission payloads.
  - Stop the start-exam response from exposing fill acceptable answers or correct matching pairs.
  - Serialize concurrent submissions for the same Student/Exam and suppress duplicate browser submissions while one request is pending.
  - Validate structured Matching and Fill in blank answers server-side; reject malformed or non-bijective Matching payloads without grading or crashing.
  - Reject duplicate question answers and recover safely when concurrent start requests race the unique Submission constraint.
  - Enforce canonical `[BLANK]` token/metadata parity before an AI question draft can be published.
  - Add focused backend contract and frontend component coverage for the repaired question types.
- Out of scope:
  - Scoring-formula changes for valid answers, database migrations, authentication, ownership, result-page answer review, and historical question-data rewrites.

## Behavior
- Before:
  - The taking page creates inputs only for `[BLANK]`, while the standard dataset uses `___`.
  - Matching buttons use content-sized inline layout, making columns and line origins ambiguous.
  - Start-exam returns raw answer-bearing `metadata_json` for matching and fill-in-blank questions.
  - A manual submit in the final second can race the timer auto-submit, while the backend reads the submission without a row lock.
  - Matching grading accepts duplicate and Cartesian-product pairs, and malformed structured payloads can raise an unhandled exception.
  - Duplicate answer entries and concurrent start requests can surface database uniqueness errors as 500 responses.
  - The AI prompt requests `[BLANK]`, but the publish boundary does not enforce token/metadata parity.
- After:
  - Both `[BLANK]` and legacy runs of three or more underscores create accessible text inputs; declared blank metadata provides a safe fallback when content has no token.
  - Matching options render as equal-width vertical lists; desktop shows connector lines and mobile shows an explicit current-match list.
  - Start-exam returns only interaction metadata: `blank_count` for fill-in-blank and independent `left_options`/`right_options` lists for matching.
  - Correct answers remain available only from the authorized post-submission result contract.
  - One shared frontend in-flight guard covers manual and timed submission; the backend locks the submission row before checking and grading it.
  - Matching grading requires unique left/right values from the expected option sets; malformed Matching or Fill in blank structures fail closed with zero points.
  - Duplicate question entries fail request validation; a concurrent start reuses the winning Submission row.
  - AI Fill in blank drafts publish only when canonical tokens, contiguous indexes, and acceptable answers agree.
- Preserved invariants:
  - Endpoint paths, submission payloads, grading behavior, BFF routing, authorization, and persisted question metadata remain unchanged.
  - Teacher/Admin authoring and post-submission review retain full question metadata.

## Expected files and contracts
- Files/modules: Student schemas/service/tests; question-generation prompt/test; Student exam types/page; matching component and component tests.
- API/event/schema impact: Approved security hardening of `GET /student/exams/{exam_id}/start`; answer-bearing raw metadata is replaced by typed interaction metadata. No endpoint or request change.
- Migration/data impact: None. Legacy `___` content remains supported without rewriting stored data.
- Security/ownership/tenant impact: Removes answer-key disclosure from the pre-submission Student response and prevents concurrent grading of one submission; existing visibility and ownership queries remain authoritative.

## Verification contract
- Targeted tests: Backend start-exam response sanitization; prompt contract; Fill in blank rendering and submission; Matching layout/keyboard/match behavior.
- Static/type checks: Scoped Ruff, frontend ESLint, and TypeScript production build.
- Integration/PostgreSQL checks: Focused Student contract suite through the guarded PostgreSQL runner, including repeat/concurrent submission behavior.
- Build/E2E/visual checks: Frontend production build and desktop/mobile browser screenshots of both question types.
- Manual verification: Start an exam containing legacy Fill in blank and Matching questions; confirm visible inputs, stable pairing UX, correct payloads, and no answer keys in the Network response.

## Rollback
- Code rollback: Revert the files listed in the task handoff.
- Data rollback: Not applicable; no persisted data or schema is changed.

## Assumptions and drift
- Verified assumptions:
  - Grading reads full persisted metadata server-side and does not require answer-bearing metadata from the Student start response.
  - The result endpoint is authorized and intentionally returns correct answers only after submission.
  - The current standard dataset has 12 Fill in blank questions using `___` and none using `[BLANK]`.
- Unresolved assumptions:
  - Duplicate matching labels remain semantically ambiguous because the persisted format identifies choices by text rather than stable option IDs; this task prevents ref overwrite in normal unique-label content but does not migrate that model.
- SPEC_DRIFT:
  - The operational start-exam response exposed answer keys despite the Student schema deliberately omitting `Option.is_correct`; this implementation aligns all question types with the intended pre-submission confidentiality boundary.
