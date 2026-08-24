# Change Contract: DATA-DEMO-001 Standard PlayStudy Demo Dataset

Risk level: L3
Owner: Codex primary agent
Approval required: Yes
Approval evidence: The owner approved the complete `demo-standard-v1` implementation plan and explicitly approved the required schema change on 2026-08-15.

## Scope

- In scope:
  - Add a versioned `demo-standard-v1` fixture for local demonstration and manual QA.
  - Add deterministic UUIDv5 identity, manifest validation, content hashing, dependency checks, and fixture inventory validation.
  - Add guarded `plan`, `apply`, `verify`, and dataset-scoped `reset` commands implemented with SQLAlchemy 2.x.
  - Bootstrap the three canonical local demo accounts (`admin`, `teacher`, and interactive `student`) when they are absent; keep the five analytics-only student passwords random and undisclosed.
  - Store six self-authored TXT/PDF learning materials through the existing local storage boundary without calling an AI provider.
  - Seed teacher-owned topics, materials, questions, exams, briefs, flashcards, learners, submissions, answers, and flashcard progress.
  - Calculate seeded answer scores with the current `GradingService`.
  - Add unit and guarded PostgreSQL integration coverage plus an English engineering handoff.
  - Deprecate the legacy detailed seed entry point so it cannot recreate ownerless content.
- Out of scope:
  - OpenAPI changes, authentication changes, or permission changes.
  - AI-generated content, AI approval state, AI provider calls, audit-event seeding, or AI golden-dataset evaluation.
  - Shared/staging/production data mutation.

## Behavior

- Before:
  - Seed utilities use legacy query patterns and can create ownerless records that violate the current ownership model.
  - There is no versioned, reproducible, idempotent, multi-subject demo dataset.
- After:
  - `python -m scripts.seed_demo_data` validates and manages only `demo-standard-v1` on a guarded local development database or an isolated `_test` database.
  - Reapplying an unchanged dataset is idempotent. Content drift is reported before mutation and must be resolved using the explicit dataset-scoped reset flow.
  - Reset removes only deterministic dataset rows and stored files; it never truncates a table or deletes unrelated data.
- Preserved invariants:
  - Teacher owns all seeded learning content; no seeded Topic or Question has a null owner.
  - Published exams and their topics have the same owner.
  - Student-visible payloads and access remain governed by existing backend services.
  - Audit tables remain append-only and are not modified by the seed lifecycle.

## Expected files and contracts

- Files/modules:
  - `backend/app/demo_data/`
  - `backend/fixtures/demo_standard_v1/`
  - `backend/scripts/seed_demo_data.py`
  - focused unit and PostgreSQL integration tests
  - The former `backend/seed_detailed_data.py` deprecation wrapper was retired from the active tree on 2026-08-20 and archived under `.legacy-archive/non-runtime-artifacts-20260820/legacy-backend-scripts/`; the supported entry point remains `python -m scripts.seed_demo_data`.
  - `docs/handoffs/DATA-DEMO-001.md`
- API/event/schema impact:
  - No API or event change.
  - A narrow Alembic migration adds `SINGLE_CHOICE` to PostgreSQL enum `questiontype` so the schema matches the existing SQLAlchemy/Python enum.
- Migration/data impact:
  - Upgrade is additive and preserves all existing question rows.
  - Downgrade refuses while any `SINGLE_CHOICE` row exists, then safely recreates the prior three-label enum after those rows are explicitly removed or converted.
  - The owner approved dropping and recreating the disposable local development database after an out-of-band enum value was detected. The migration itself remains fail-closed and accepts only the exact historical three-label schema.
  - Explicit local demo-data insertion and exact dataset-scoped reset only.
- Security/ownership/tenant impact:
  - No authorization rule changes.
  - Loader validates local/test database targeting, deterministic ownership, cross-resource consistency, and stored-file isolation.

## Verification contract

- Targeted tests:
  - Manifest validation, deterministic IDs, duplicate/reference validation, question-answer validation, dependency order, file validation, and content hash.
- Static/type checks:
  - Ruff and mypy over new/affected modules; `git diff --check`.
- Integration/PostgreSQL checks:
  - Migration `upgrade -> downgrade -> upgrade` on guarded PostgreSQL with exact enum-label order and column-contract assertions.
  - Downgrade refusal remains atomic while `SINGLE_CHOICE` rows exist and preserves pre-existing non-single-choice rows.
  - Guarded `apply -> verify -> apply -> reset` lifecycle.
  - Mid-transaction failure rollback and unrelated-row preservation.
  - Ownership/visibility, material access, grading, reporting, and flashcard review behavior.
- Build/E2E/visual checks:
  - No frontend build is required because no frontend code changes.
  - Render and inspect all three PDF fixture files.
- Manual verification:
  - Apply and verify `demo-standard-v1` on the local development PostgreSQL database, then confirm a second plan is unchanged.

## Rollback

- Code rollback: Revert only the DATA-DEMO-001 fixture, loader, migration, tests, deprecation wrapper, and handoff files.
- Data rollback: Run `uv run --frozen python -m scripts.seed_demo_data reset --confirm demo-standard-v1`, then downgrade to `ca82f9a51d44`. The downgrade refuses while any `SINGLE_CHOICE` row remains.

## Assumptions and drift

- Verified assumptions:
  - The pre-change Alembic head was `ca82f9a51d44`; the approved enum migration advances the expected head to `a83c1d7e9f02`.
  - The current model has 14 tables and explicit Topic/Question ownership.
  - `GradingService` is the grading authority used by student submission.
  - The existing `LocalFileStorage` boundary prevents paths escaping its configured root.
  - The local target was verified as `development` on `localhost:5432/test_project_db` before the owner-approved recreation; the isolated test database remained separate.
- Unresolved assumptions:
  - None. The owner approved the narrow forward migration required to resolve the enum drift.
- SPEC_DRIFT:
  - The legacy detailed seed script uses `Session.query()` and creates ownerless Topic/Question records.
  - The current grading service does not grade `SINGLE_CHOICE` explicitly. Seeded published exams therefore use only question types that the current service grades; single-choice coverage remains in the draft exams and question bank.
  - Model/schema drift: `app.models.enums.QuestionType` declares `SINGLE_CHOICE`, but revision `73f523515ba5` created the PostgreSQL enum without that label and no later revision added it. Model-only `create_all` tests mask this drift; an Alembic-upgraded PostgreSQL database rejects the value.
