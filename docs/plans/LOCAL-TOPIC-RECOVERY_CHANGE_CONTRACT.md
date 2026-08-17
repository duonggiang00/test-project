# Change Contract: LOCAL-DATA-001 Topic recovery and test-data cleanup

Risk level: L3
Owner: Codex primary agent
Approval required: Yes
Approval evidence: The owner explicitly requested diagnosis of Topic retrieval and removal of accumulated test data on 2026-08-15.

## Scope
- In scope:
  - Diagnose the local `GET /topics` failure.
  - Upgrade the verified local development PostgreSQL database from Alembic
    `b57c9a14d2e8` to the already approved head `ca82f9a51d44`.
  - Remove accumulated fixture, E2E, mock, seed-content, and audit rows.
  - Preserve only the three canonical local login accounts:
    `admin@example.com`, `teacher@example.com`, and `student@example.com`.
  - Remove orphaned files from the verified local `backend/uploads` storage root.
- Out of scope:
  - Source behavior, API, authentication, authorization, or migration changes.
  - Any remote, shared, staging, or production database.
  - Resuming the Teacher/Admin workflow redesign in the same cleanup operation.

## Behavior
- Before:
  - Current code queries `topics.owner_id`, while the local database is still at
    `b57c9a14d2e8` and does not contain that column.
  - The local database contains hundreds of accumulated fixture users and mock
    business records; local upload storage contains test files.
- After:
  - The local database is at `ca82f9a51d44` and Topic queries match the schema.
  - All business/audit rows and non-canonical test users are absent.
  - The three canonical local accounts remain available for login.
  - Local upload storage contains no files.
- Preserved invariants:
  - Migration history and application schemas are not edited.
  - Database cleanup runs only after validating localhost, development mode,
    the exact database name `test_project_db`, and example-only email domains.

## Expected files and contracts
- Files/modules:
  - This change contract and temporary diagnostics only.
- API/event/schema impact:
  - No contract change; local schema advances to the existing approved head.
- Migration/data impact:
  - Destructive reset of verified local test/demo data.
- Security/ownership/tenant impact:
  - No policy change. All deleted records were classified as local test/demo
    data; no non-example email domain was found.

## Verification contract
- Targeted tests:
  - Direct authenticated Topic list and create probe with canonical local users.
- Static/type checks:
  - Not applicable because application source is unchanged.
- Integration/PostgreSQL checks:
  - Alembic current equals `ca82f9a51d44`.
  - All application tables are empty except the three canonical users.
- Build/E2E/visual checks:
  - Not required for a local data reset; no frontend source changes.
- Manual verification:
  - Confirm `GET /topics` returns a canonical empty page and a teacher can create
    then delete a Topic.

## Rollback
- Code rollback:
  - Remove this documentation artifact if no longer needed.
- Data rollback:
  - Deleted test/demo rows and upload files are not recoverable from the
    application. Recreate clean sample data with the repository seed scripts.

## Assumptions and drift
- Verified assumptions:
  - Target host is `localhost`, environment is `development`, and database is
    exactly `test_project_db`.
  - All 338 users use `example.com` or `example.test`; 333 are generated fixture
    identities, three are canonical seed identities, and two are named test
    identities.
  - Existing Topics and Exams are seed/mock/E2E records.
- Unresolved assumptions:
  - None.
- SPEC_DRIFT:
  - Local schema lagged the checked-out approved migration, causing Topic reads
    to fail before authorization or pagination completed.

## Completion evidence
- Alembic upgraded `b57c9a14d2e8 -> ca82f9a51d44`; `alembic current`
  reports the head and `alembic check` reports no new operations.
- Cleanup changed database counts from 338 users, 4 topics, 57 exams,
  266 questions, 532 options, 17 submissions, 11 materials, 59 chunks,
  and 11 audit events to three canonical users and zero rows in every other
  application table.
- Local upload cleanup removed 27 files totaling 8,900,102 bytes; zero files
  remain under `backend/uploads`.
- An authenticated teacher probe passed empty Topic list, Topic create, list,
  detail, delete, and final empty list; the temporary Topic was removed.
