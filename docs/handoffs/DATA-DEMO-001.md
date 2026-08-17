# Handoff: DATA-DEMO-001 standard PlayStudy demo dataset

Status: DONE
Risk level: L3

## Outcome

- Summary: Added the versioned `demo-standard-v1` dataset, a guarded SQLAlchemy 2.x lifecycle CLI, six self-authored learning materials, deterministic learning-data identities, canonical local demo accounts, and a reversible PostgreSQL enum migration for `SINGLE_CHOICE`. The owner-approved local development database was recreated, migrated to head, loaded, verified, and proven idempotent.
- Requirements/task IDs: DATA-DEMO-001.

## Files changed

- `backend/app/demo_data/` — strict fixture models, hash/reference validation, deterministic IDs, guarded plan/apply/verify/reset behavior, exact content checks, grading checks, and dataset-scoped cleanup.
- `backend/fixtures/demo_standard_v1/` — versioned manifest, JSON fixture groups, three TXT files, three rendered PDF files, and the deterministic fixture builder.
- `backend/scripts/seed_demo_data.py` — CLI entry point for `plan`, `apply`, `verify`, and confirmed `reset`.
- `backend/app/services/material_processing.py` — reusable extraction and chunking logic shared by material processing and the demo loader.
- `backend/app/services/ai_service.py` — reuses the material-processing boundary instead of duplicating extraction logic.
- `backend/app/services/grading_service.py` — type-safe numeric conversion while keeping the existing grading behavior.
- `backend/alembic/versions/a83c1d7e9f02_add_single_choice_question_type.py` — fail-closed enum upgrade and data-aware reversible downgrade.
- `backend/scripts/run_migration_roundtrip.py` and `backend/tests/unit/test_migration_roundtrip.py` — exact enum order/column checks, data preservation, and downgrade-refusal coverage.
- `backend/tests/unit/test_demo_data_fixture.py` and `backend/tests/test_demo_data_loader.py` — validation, lifecycle, rollback, visibility, storage, grading, reporting, and review-flow coverage.
- `backend/seed_detailed_data.py` — deprecated legacy ownerless seed entry point.
- `backend/pyproject.toml`, `config/database-model-signature.json` — gate coverage and Alembic head synchronization.
- `docs/plans/DATA-DEMO-001_CHANGE_CONTRACT.md` — approved scope, local reset decision, verification, and rollback contract.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `uv run --frozen pytest -q tests/unit/test_migration_roundtrip.py tests/unit/test_demo_data_fixture.py` | 0 | 59 | 59 | 0 | 0 | Migration-schema validators and fixture validation passed. |
| `uv run --frozen python -m scripts.run_migration_roundtrip` | 0 | n/a | n/a | 0 | 0 | Fresh upgrade, exact head, downgrade refusal with a `SINGLE_CHOICE` row, clean downgrade, base, and re-upgrade passed; isolated database dropped. |
| `uv run --frozen python -m scripts.run_integration -- -q tests/test_demo_data_loader.py` | 0 | 2 | 2 | 0 | 0 | Apply/verify/reapply/reset, API visibility, file isolation, scoring, reporting, flashcard review, and injected rollback passed. |
| `uv run --frozen pytest -q tests/unit` | 0 | 150 | 150 | 0 | 0 | Complete unit suite passed. |
| `uv run --frozen mypy` | 0 | 22 files | 22 files | 0 | 0 | No typing issues. |
| focused `ruff check` | 0 | n/a | n/a | 0 | 0 | All affected backend modules and tests passed. |
| `uv run --frozen alembic current` | 0 | n/a | n/a | 0 | 0 | Local database is at `a83c1d7e9f02 (head)`. |
| `uv run --frozen alembic check` | 0 | n/a | n/a | 0 | 0 | No new upgrade operations detected. |
| `node scripts/project-inventory.mjs generate` and `check` | 0 | 305 files | 305 files | 0 | 0 | Inventory source-tree hash is current. |
| `plan -> apply -> verify -> plan` on local PostgreSQL | 0 | n/a | n/a | 0 | 0 | Initial counts were created; final plan reported every row unchanged and zero conflicts. |
| Full guarded suite via `scripts.run_integration -- -q` | 1 | 223 | 221 | 2 | 0 | Only two pre-existing unit configuration cases failed because the integration runner intentionally sets `ENV=test`; the focused unit and PostgreSQL suites above pass independently. |

## Impact

- API/event/schema contract: No API or event payload changed. PostgreSQL `public.questiontype` now includes `SINGLE_CHOICE` in the model-declared order.
- Migration/data: New head is `a83c1d7e9f02`. Upgrade accepts only the exact historical three-label enum. Downgrade refuses while any `SINGLE_CHOICE` question exists, then rebuilds the prior three-label enum without losing other question rows.
- Security/ownership/tenant: Loader is restricted to localhost PostgreSQL in `development`, or an `_test` database in `test`. Teacher owns all learning content; student visibility uses production authorization services; stored files remain under the dataset namespace. No audit event is seeded.
- Dependency/toolchain: No dependency was added. Existing `uv`, SQLAlchemy, ReportLab, PDF extraction, and local storage capabilities are reused.

## Manual evidence

- Scenario: Recreated only `localhost:5432/test_project_db` after validating `ENV=development`, exact database name, and separation from `test_project_db_test`; applied Alembic from base to head.
- Result: Local inventory is 9 Topics, 6 Materials/Chunks/Briefs/Decks, 60 Questions, 144 Options, 48 Flashcards, 6 Exams, 15 Submissions, 120 Answers, 24 Progress rows, 5 analytics students, and 3 canonical login accounts. Submitted score range is 20–100.
- Scenario: Authenticated read-only API probe with the local demo accounts.
- Result: Admin and Teacher each see 9 Topics; Student sees 3 published Exams. All three canonical accounts authenticate with the local-only password `12345678`.
- Scenario: Rendered all three PDFs to PNG at 150 DPI and inspected each complete A4 page.
- Result: Vietnamese and English text render correctly with no clipping, overflow, blank page, or missing glyph.
- Screenshot/trace: `tmp/pdf-qa-final/` was temporary visual-QA output and is removed after verification; the source PDFs remain in the fixture.
- Independent review: Migration reviewer found no P1/P2 issue after rerunning the exact schema/data lifecycle, Ruff, 44 migration units, and database-signature drift check. The reviewer's isolated database was confirmed absent afterward.

## Usage

From `backend/`:

```text
uv run --frozen python -m scripts.seed_demo_data plan
uv run --frozen python -m scripts.seed_demo_data apply
uv run --frozen python -m scripts.seed_demo_data verify
uv run --frozen python -m scripts.seed_demo_data reset --confirm demo-standard-v1
```

Local-only demo logins:

- `admin@example.com` / `12345678`
- `teacher@example.com` / `12345678`
- `student@example.com` / `12345678`

The five analytics-only Student passwords are random, are not printed, and are not intended for manual login.

## Risks and follow-up

- Known risks: `SINGLE_CHOICE` exists in schema and draft/question-bank data, but the current grading service still lacks an explicit single-choice grading branch. Published demo exams therefore contain only currently gradeable types.
- Known risks: The local demo password is intentionally weak and valid only because the CLI is hard-blocked outside local development/test targets. It must never be reused for shared or production environments.
- Unverified items: Full-suite composition still has two pre-existing configuration-test failures when unit tests inherit the integration runner's `ENV=test`; the same 150 unit tests pass in their intended environment. A dedicated PostgreSQL negative probe for an unsupported upgrade label set is not included; the migration uses direct exact-label equality and intentionally refuses such databases.
- Follow-up tasks: Add explicit `SINGLE_CHOICE` grading before publishing that type; separate unit and PostgreSQL commands in the aggregate gate so unit configuration tests do not inherit integration environment state.

## Rollback

- Code: Revert only the DATA-DEMO-001 files listed above and restore the prior database signature head.
- Data: Run `uv run --frozen python -m scripts.seed_demo_data reset --confirm demo-standard-v1`. Remove or convert any remaining `SINGLE_CHOICE` questions, then run `uv run --frozen alembic downgrade ca82f9a51d44`.
