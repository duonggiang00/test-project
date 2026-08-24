# Handoff: AI-RAG-HIDE-001 — Temporarily disable RAG

Status: REVIEW  
Risk level: L3 — governed sensitive retrieval behavior

## Outcome

- Summary: Material chat and the legacy RAG processing route are disabled by default at both backend and frontend boundaries. Upload, extraction, document chunks, Questions, Flashcards, Topic Brief generation, human review, and publication remain available. The PlayStudy Google Docs report no longer describes RAG or document chat.
- Requirements/task IDs: `AI-RAG-HIDE-001`

## Files changed

- `.env.example` — documents the default-off backend and frontend feature flags.
- `backend/app/core/config.py` — adds the authoritative `RAG_ENABLED` setting.
- `backend/app/api/endpoints/ai_studio.py` — fails closed on both RAG routes before authentication, retrieval, or provider work.
- `backend/tests/contract/test_rag_feature_flag.py` — verifies the default and canonical disabled response.
- `backend/tests/test_ai_studio.py` — preserves enabled legacy RAG regression coverage.
- `backend/tests/test_authorization_idor.py` — explicitly enables RAG for the retained material-isolation regression.
- `frontend/src/app/(admin)/ai-workspace/page.tsx` — hides material chat and presents the generation-only workspace by default.
- `frontend/src/lib/errors.ts` — adds the safe user-facing feature-unavailable translation.
- `frontend/tests/component/ai-workspace-errors.test.tsx` — verifies chat absence/non-call and retained generation actions.
- `docs/spec/CANONICAL_PROJECT_SPEC.md` — records the temporary suspension without deleting historical capability.
- `docs/plans/AI-RAG-HIDE-001_CHANGE_CONTRACT.md` — records scope, approval, invariants, and rollback.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — records implementation and review status.
- Google Doc `16_zCStwiQTuMBRmvs8ILsV3CG6RhqZJivYOd4yDgPRo`, tab `t.0` — removes RAG/chat claims while preserving generation content.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `uv run --frozen pytest -q tests/contract/test_rag_feature_flag.py tests/unit/test_ai_studio_chat_generator.py` | 0 | 9 | 9 | 0 | 0 | Default-off guard and retained generator regression pass. |
| `uv run --frozen ruff check ...` (five changed backend/test files) | 0 | — | — | 0 | — | All checks passed. |
| `uv run --frozen mypy --follow-imports=skip app/core/config.py app/api/endpoints/ai_studio.py` | 0 | 2 files | 2 files | 0 | 0 | No type issues in the changed backend modules. |
| `uv run --frozen python -m scripts.run_integration -- -q tests/test_ai_studio.py tests/test_authorization_idor.py` | 0 | 10 | 10 | 0 | 0 | Enabled RAG regressions and ownership checks pass; isolated PostgreSQL database was dropped. |
| `uv run --frozen python -m scripts.run_integration -- -q tests/test_ai_generation_review.py` | 0 | 15 | 15 | 0 | 0 | Generation, review, approval, and publication remain functional; isolated PostgreSQL database was dropped. |
| `node .../jest.js --runInBand tests/component/ai-workspace-errors.test.tsx tests/component/generation-job-review.test.tsx src/services/apiService.test.ts` | 0 | 38 | 38 | 0 | 0 | Chat is hidden/non-calling by default and generation/review service behavior is preserved. |
| `node .../eslint.js` (changed frontend files) | 0 | 3 files | 3 files | 0 | 0 | Scoped frontend lint passes. |
| `node .../next build --webpack` | 0 | 20 pages | 20 pages | 0 | 0 | Production compilation and TypeScript checks pass. |
| `playwright test tests/e2e/ai-review-flow.spec.ts --config=playwright.mocked.config.ts` | 0 | 4 | 4 | 0 | 0 | AI review flow passes on Chromium, Firefox, WebKit, and mobile Chrome. |
| `git diff --check` | 0 | — | — | 0 | — | No whitespace errors. |

## Impact

- API/event/schema contract: The two existing RAG endpoints remain in the API but return canonical `404 FEATURE_NOT_AVAILABLE` when the default-off backend flag is active. No payload, event, or schema is changed.
- Migration/data: None. Existing chunks, embedding fields, and RAG implementation are retained.
- Security/ownership/tenant: The disabled-route guard executes before authentication, database retrieval, and provider access. Enabled generation routes keep their existing backend ownership enforcement.
- Dependency/toolchain: No dependency or package-manager change.

## Manual evidence

- Scenario: Google Docs readback of the only report document and tab after revision-guarded native edits.
- Result: Title `Khung báo cáo dự án mẫu`; document ID `16_zCStwiQTuMBRmvs8ILsV3CG6RhqZJivYOd4yDgPRo`; tab `t.0`; 587 paragraphs; 16 native tables; zero content matches for `RAG`, `AI/RAG`, `retrieval-augmented`, `ngữ cảnh truy xuất`, `chatbot`, and `chat với tài liệu`.
- Screenshot/trace: Four-browser Playwright result above; no PDF or DOCX export was requested or produced.

## Risks and follow-up

- Known risks: The backend and frontend flags are intentionally separate; the backend remains authoritative if presentation configuration drifts.
- Unverified items: Independent L3 review has not been performed in this implementation turn. The repository-configured broader mypy invocation also expands beyond the requested files and currently reports 10 errors in untouched `app/services/ai_generation_service.py`; the changed backend modules pass the scoped mypy command recorded above.
- Follow-up tasks: Obtain independent security/behavior review, then mark the tracker item `DONE` if no P1/P2 findings remain.

## Rollback

- Code: Set `RAG_ENABLED=true` and `NEXT_PUBLIC_RAG_ENABLED=true` to restore the retained implementation; revert the presentation/spec/report wording when RAG returns to product scope.
- Data: None.
