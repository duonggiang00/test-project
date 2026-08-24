# Handoff: STUDENT-EXAM-QUESTION-001 Safe question interaction repair

Status: DONE
Risk level: L3

## Outcome
- Summary: Repaired Student Fill in blank and Matching rendering, removed pre-submission answer-key metadata, hardened structured grading, and serialized the Student exam start/submit lifecycle.
- Requirements/task IDs: `STUDENT-EXAM-QUESTION-001`.

## Files changed
- `docs/plans/STUDENT-EXAM-QUESTION-001_CHANGE_CONTRACT.md` — approved scope, risk, behavior, verification, and rollback.
- `docs/spec/CANONICAL_PROJECT_SPEC.md` — pre-submission Student question-metadata confidentiality rule.
- `backend/app/schemas/student.py` — typed safe interaction metadata and duplicate-question submission validation.
- `backend/app/schemas/ai_generation.py` — canonical AI Fill in blank draft invariant.
- `backend/app/services/student_service.py` — safe start payload, CSPRNG Matching option order, concurrent-start recovery, and submission row locking.
- `backend/app/services/grading_service.py` — fail-closed Fill in blank parsing and one-to-one Matching validation.
- `backend/app/ai/prompts/question_generation_v1.py` — prompt v3 canonical `[BLANK]` instruction.
- `backend/tests/test_student.py` — start/submit API regressions.
- `backend/tests/test_student_concurrency.py` — deterministic two-Session PostgreSQL start/submit race coverage.
- `backend/tests/test_ai_generation_review.py` — invalid AI Fill in blank publish rollback coverage.
- `backend/tests/unit/test_grading_structured_answers.py` — malformed and Cartesian-product grading regressions.
- `backend/tests/unit/test_question_draft_contract.py` — canonical/mixed Fill in blank draft validation.
- `backend/tests/unit/test_question_generation_prompt.py` — prompt contract.
- `frontend/src/app/student/exam/[id]/page.tsx` — legacy/canonical blank inputs, safe Matching metadata, stable timer, and shared submission guard.
- `frontend/src/components/features/student/BrutalistMatchingUI.tsx` — equal-width desktop columns, responsive connectors, and mobile answer/result summaries.
- `frontend/src/types/index.ts` — typed Student interaction metadata.
- `frontend/tests/component/student-exam-errors.test.tsx` — rendering, payload, and final-second duplicate-submit regressions.
- `frontend/tests/component/student-flashcard-accessibility.test.tsx` — Matching keyboard, layout, mobile, and result coverage.
- `docs/generated/openapi.json` — regenerated API contract.
- `docs/generated/project-inventory.json` — regenerated technical inventory.

## Verification
| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `uv run --frozen pytest -q -p no:cacheprovider -m "unit or contract"` | 0 | 336 | 336 | 0 | 162 | Full backend unit/contract regression passed after all focused additions. |
| `uv run --frozen python -m scripts.run_integration -- -q -p no:cacheprovider tests/test_student.py tests/test_ai_generation_review.py` | 0 | 23 | 23 | 0 | 0 | Guarded PostgreSQL Student and AI-review behavior passed; DB was created and dropped. |
| `uv run --frozen python -m scripts.run_integration -- -q -p no:cacheprovider tests/test_student_concurrency.py` | 0 | 1 | 1 | 0 | 0 | Deterministic concurrent start/submit regression passed; DB was created and dropped. |
| `uv run --frozen pytest -q -p no:cacheprovider tests/unit/test_question_draft_contract.py tests/unit/test_question_generation_prompt.py tests/unit/test_grading_structured_answers.py` | 0 | 16 | 16 | 0 | 0 | Structured grading, AI draft, and prompt contracts passed. |
| `node node_modules/jest/bin/jest.js --runInBand` | 0 | 132 | 132 | 0 | 0 | Full frontend Jest suite passed. |
| `node node_modules/jest/bin/jest.js --runInBand --runTestsByPath tests/component/student-exam-errors.test.tsx tests/component/student-flashcard-accessibility.test.tsx --detectOpenHandles` | 0 | 8 | 8 | 0 | 0 | Focused Student question UI suite passed. |
| `npm run lint` | 0 | n/a | n/a | 0 | n/a | Frontend ESLint passed with no errors or warnings after cleanup. |
| `npm run build` | 0 | 20 routes | 20 routes | 0 | 0 | Next.js 16.2.10 production build and TypeScript passed. |
| `uv run --frozen ruff check ...` | 0 | n/a | n/a | 0 | n/a | Scoped backend Ruff checks passed. |
| `node scripts/openapi-contract.mjs check` | 0 | 60 paths | 60 paths | 0 | 0 | Generated OpenAPI matches runtime. |
| `node scripts/architecture-guard.mjs check` | 0 | 123 fingerprints | 123 | 0 | 0 | Current violations remain below baseline 150. |
| `node scripts/project-inventory.mjs check` | 0 | 374 files | 374 files | 0 | 0 | Generated inventory matched the source tree at verification time. |

## Impact
- API/event/schema contract: `GET /student/exams/{exam_id}/start` now exposes only `blank_count` or independently ordered Matching option lists. Duplicate question entries in a submit request return canonical `VALIDATION_ERROR`. Endpoint paths and submission payload shapes are unchanged.
- Migration/data: No migration and no persisted-data rewrite.
- Security/ownership/tenant: Pre-submission answer keys are no longer exposed. Matching Cartesian-product attacks fail closed. Concurrent start/submit requests converge on one retained grade and one audit event. Existing ownership queries remain authoritative.
- Dependency/toolchain: No dependency changes.

## Manual evidence
- Scenario: Production frontend rendered a legacy `___` Fill in blank question and accepted typed input.
- Result: The input was visible, keyboard-accessible, and included in the unchanged submission payload.
- Screenshot/trace: `C:/Users/Acer/.codex/visualizations/2026/08/05/019fcfe6-1e2e-7191-90cd-056fd2b9ff43/playstudy-fill-in-blank-fixed.png`.
- Scenario: Production frontend rendered safe Matching metadata at desktop and mobile widths.
- Result: Desktop displayed two aligned columns and connector lines; mobile displayed vertical options and an explicit matched-pair summary.
- Screenshot/trace: `C:/Users/Acer/.codex/visualizations/2026/08/05/019fcfe6-1e2e-7191-90cd-056fd2b9ff43/playstudy-matching-fixed-desktop.png`; `C:/Users/Acer/.codex/visualizations/2026/08/05/019fcfe6-1e2e-7191-90cd-056fd2b9ff43/playstudy-matching-fixed-mobile.png`.
- Independent review: Final L3 review reported no remaining P1/P2 findings and confirmed the deterministic PostgreSQL concurrency proof.

## Risks and follow-up
- Known risks: Persisted Matching choices are text-based; duplicate labels remain semantically ambiguous. A future schema change should use stable option identifiers if duplicate labels must be supported.
- Unverified items: Firefox/WebKit visual rendering was not rerun for this focused repair.
- Follow-up tasks: Consider extracting shared structured-question validation for Teacher-authored and AI-authored questions when the authoring contract is next revised.

## Rollback
- Code: Revert the task-scoped files above while preserving unrelated worktree changes.
- Data: None required.
