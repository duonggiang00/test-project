# Remaining Work Execution Plan — 2026-08-25

Status: Approved for staged implementation
Owner: Project owner
Execution owner: Primary coding agent

## Decisions

- External Google Docs and report-generation artifacts are out of scope.
- Complete the active RAG and Exam independent reviews before starting new debt work.
- Repair the canonical coverage runner before raising the frontend baseline.
- Tighten the static-production CSP without forcing nonce-based dynamic rendering.
- Convert hard-coded frontend UI text and comments to English in four bounded waves.
- Build a 40-case, Vietnamese-first golden dataset. Only owner/admin-approved reference
  content may enter the approved dataset.
- Use two-tier AI evaluation: deterministic pull-request checks, capped live evaluation
  for AI-affecting changes after three stable baseline runs, and a weekly/manual full run.
- Quality metrics may fall no more than five percentage points below the approved
  baseline. Structure, citation validity, and prompt-injection safety remain hard 100%
  gates. P95 latency and mean estimated cost may rise no more than 20%.
- Implement semantic hybrid RAG after AI-006 through AI-008. Install pgvector locally,
  align CI with PostgreSQL 18/pgvector 0.8.6, and retain lexical mode as runtime rollback.
- Remove the compatibility-only `POST /ai/process-document` endpoint when semantic RAG
  replaces mock embeddings. This breaking removal is explicitly owner-approved.
- AI grading production flow remains outside this program.

## Delivery order

1. `AI-RAG-ENABLE-001` and `EXAM-FLOW-QUICK-001`: independent review, finding
   remediation, exact verification, handoff, and release.
2. `TOOL-PYTEST-CACHE-001`: make coverage execution independent of an inaccessible
   `.pytest_cache`; diagnose and repair any Jest leaked handle rather than forcing exit.
3. `SEC-CSP-001`: remove unused origins and production `unsafe-eval`; retain the static
   App Router compatible `unsafe-inline` residual risk.
4. `UI-LANGUAGE-001` and `TEST-FE-COVERAGE-001`: translate public/auth, admin/AI,
   exam, and student/shared surfaces in four reviewable waves while increasing coverage.
5. `AI-006`: validate a versioned 40-case dataset covering chat/retrieval (16), question
   generation (12), flashcards (6), and topic briefs (6).
6. `AI-007`: measure correctness, groundedness, relevance, citation validity, injection
   resistance, latency, token usage, and configured cost without committing raw payloads.
7. `AI-008`: add deterministic CI, establish three stable live baselines, then gate
   AI-affecting pull requests with a capped 20-case subset and run all 40 weekly/manual.
8. `RAG-SEMANTIC-001`: add a typed embedding provider, real chunk embeddings,
   pgvector storage/indexing, vector-plus-full-text reciprocal-rank fusion, source events,
   and the approved legacy endpoint removal.

## Acceptance boundaries

- One implementation owner per task; L2/L3/L4 tasks receive independent review.
- Every non-trivial task has a change contract and handoff.
- Browser traffic remains BFF-only and backend ownership checks remain authoritative.
- Local destructive database work targets only the explicitly configured development or
  isolated test database. Shared environments are never mutated.
- Frontend critical modules reach approximately 80% meaningful line coverage. The global
  frontend target is `max(25%, fresh baseline + 10 percentage points)` and the committed
  baseline is never reduced.
- Semantic RAG does not become the default until the approved evaluation suite meets all
  safety and regression thresholds.
- Required gates are the relevant targeted tests followed by `fast`, `architecture`,
  `coverage`, PostgreSQL `integration`, `migration`, mocked E2E, real E2E, and AI evals.
- `.claude/`, external reports, raw provider payloads, secrets, and ignored test artifacts
  are never staged.

## Rollback checkpoints

- Active chat: set `RAG_ENABLED=false` and `NEXT_PUBLIC_RAG_ENABLED=false`.
- CSP: revert only the policy commit if a verified production dependency is blocked.
- AI regression gate: keep live evaluation non-required until three stable full runs exist.
- Semantic retrieval: set `RAG_RETRIEVAL_MODE=lexical`; disable chat only if the
  backend-authoritative RAG kill switch is required.
- Database: use the downgrade path only on isolated databases; development data may be
  dropped and recreated under the owner's approved development policy.
