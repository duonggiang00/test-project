# Change Contract: BASE-001 Standardize the Grade-Correction Feature

Risk level: L3
Owner: Primary implementation agent
Approval required: Yes
Approval evidence: The project owner directed this work explicitly in
conversation on 2026-08-19/20, instructing that the grade-correction
capability already implemented under GRADE-001 (commits `f01c85b`, `2afc2c8`,
`16d946e`, `c1a8ed1`, `e087844`, `3fcc57e`) be packaged and standardized as an
official product feature, with explicit English/black-and-white UI and
production-build E2E requirements.

## Scope

In scope:

- Package the already-implemented and already independently-reviewed
  GRADE-001 feature (a teacher or admin correcting one submission answer's
  score, with a mandatory reason, an atomic audit event, and a recomputed
  submission total) into formal governance artifacts: this change contract,
  a scoped task tracker, and a handoff.
- Extend the guarded migration round-trip runner
  (`backend/scripts/run_migration_roundtrip.py`) with exact schema
  assertions (column type/nullability, the `overridden_by_id` foreign key's
  `ON DELETE SET NULL` behavior specifically, and the index) for the three
  grade-override-trail columns on `submission_answers`, in addition to the
  downgrade-refusal-while-corrected-rows-exist guard already added during
  GRADE-001's independent review.
- Convert the History submission-detail UI
  (`frontend/src/app/(admin)/history/[id]/page.tsx` and
  `AnswerGradeEditor.tsx`) from Vietnamese to English and from a mixed
  black/white/gray palette to strict black-and-white, per the root
  `AGENTS.md` UI-language rule and the project's brutalist design system.
  No validation, authorization, or data-flow behavior changes.
- Stabilize the mocked Playwright E2E suite on a dedicated production build
  (`NEXT_DIST_DIR=.next-e2e-mocked`, `next build --webpack`, then
  `next start`) instead of a dev server, with an explicit `webServer`
  startup timeout and guaranteed capture of logs/screenshots/traces on
  failure.
- A final independent review consolidating and re-verifying the
  authorization, 404-indistinguishability, bounds, total-recomputation,
  audit-atomicity, and concurrency invariants already checked during
  GRADE-001's original review.

Out of scope (explicitly excluded by the owner):

- SEC-003 through SEC-007 (access/refresh token lifecycle, revocation,
  CSRF, canonical redirect verification).
- GitHub Actions configuration, branch protection, or any deployment work.
- The downstream Topic → Material → Generate/Manual Content → Review →
  Exam → Publish → Submission → Grade → Report flow the owner named as the
  eventual target; that is separate, larger work to be scoped in a later
  change contract, not part of BASE-001.
- Any change to the grade-correction API contract, permission model, or
  audit schema — GRADE-001's design is retained as-is, only packaged and
  hardened.

## Behavior

- Before: GRADE-001 was implemented, tested, and independently reviewed,
  but not packaged as a tracked, documented product feature; its History UI
  used Vietnamese text and non-brutalist gray tokens; its mocked E2E ran
  against a Next.js dev server; and its migration guard proved a downgrade
  is refused while corrected rows exist, but nothing asserted the *exact*
  shape (type, nullability, FK delete-behavior, index) the upgrade
  produces.
- After: the feature has a change contract, a task tracker, and a handoff;
  the History UI is English-only and strictly black-and-white with intact
  keyboard/focus/error-state behavior; the mocked E2E suite runs against a
  production build with an explicit timeout and guaranteed failure
  artifacts; and the migration round trip asserts the exact grade-override
  schema at every checkpoint.
- Preserved invariants: the `PUT
  /history/submissions/{submission_id}/answers/{question_id}/grade`
  contract is unchanged — request body is exactly `{points_awarded,
  reason}`; response is the full `SubmissionDetailResponse` including
  `max_points`, `override_reason`, `overridden_at`. Ownership scoping
  (`Permission.GRADE_OWNED_EXAM_SUBMISSION`, exam-creator ownership),
  bounds (`[0, question.points]`), total recomputation, `is_correct`
  derivation, `Submission.status` preservation, and the audit
  redaction split (reason never enters `audit_events`) are all unchanged.

## Expected files and contracts

- `backend/scripts/run_migration_roundtrip.py` — exact grade-override
  column/FK/index assertions (already landed, commit `3fcc57e`).
- `frontend/src/app/(admin)/history/[id]/page.tsx`,
  `frontend/src/app/(admin)/history/[id]/AnswerGradeEditor.tsx` — English
  text, black-and-white-only styling.
- `frontend/tests/component/submission-grade-override.test.tsx`,
  `frontend/tests/e2e/grade-submission-flow.spec.ts` — updated to assert
  the English copy.
- `frontend/playwright.mocked.config.ts`, and wherever
  `scripts/verify.mjs`'s `e2e-mocked` mode invokes the production build —
  dedicated build + `next start` webServer, explicit timeout, failure
  artifact capture.
- `docs/plans/BASE-001_TASK_TRACKER.md`, `docs/handoffs/BASE-001.md`.

API/event/schema impact: none. This contract changes no request/response
shape, no migration content (only test coverage of the existing one), and
no audit action.

## Verification contract

- `node scripts/verify.mjs fast`.
- Guarded PostgreSQL integration suite (`uv run --frozen python -m
  scripts.run_integration` from `backend/`).
- Guarded migration round trip (`uv run --frozen python -m
  scripts.run_migration_roundtrip` from `backend/`), including the new
  exact-schema grade-override assertions at every checkpoint.
- `node scripts/verify.mjs e2e-mocked` against the production-build
  webServer, plus a deliberate-failure proof that artifacts are actually
  captured.
- Independent review of the invariants listed above, re-verified against
  the code (not re-trusted from the original GRADE-001 review).

## Rollback

- Code: revert the relevant commit(s). The grade-override-trail columns
  and their schema assertions may remain — they are additive and were
  already covered by GRADE-001's own rollback guidance.
- No migration, permission, or audit-schema change is introduced by this
  contract, so there is no data rollback concern beyond what GRADE-001
  already documented.

## Assumptions and drift

- Verified assumption: GRADE-001's backend contract, authorization model,
  and audit design are correct as shipped and independently reviewed; this
  contract does not re-open those design decisions.
- SPEC_DRIFT (pre-existing, not introduced or resolved here): the
  permission matrix describes student result visibility as gated "when
  released," but no release mechanism exists — a corrected grade is
  visible to the student immediately. Tracked separately, not addressed by
  BASE-001.
