# Handoff: DATA-DEMO-002 minimum-revision dataset compatibility

Status: DONE
Risk level: L2

## Outcome

- Summary: `demo-standard-v1`'s manifest no longer pins an exact Alembic
  head (which had already gone stale — it still named `f9f952e6df1a` three
  heads after that stopped being current). It now names a
  `minimum_alembic_revision`, and the loader requires the live database to
  sit at the repository's actual current head (computed live from the
  Alembic scripts, never trusted from a stored value) and requires that
  head to be a linear descendant of the minimum revision. The
  owner-authorized local database reset was performed once: drop/recreate,
  upgrade to head, and a `plan → apply → verify → apply → verify` cycle
  proving the dataset loads cleanly and idempotently.
- Requirements/task IDs: DATA-DEMO-002.

## Files changed

- `backend/app/demo_data/fixture.py` — `DemoManifest.minimum_alembic_revision`.
- `backend/app/demo_data/loader.py` — `DemoDataManager._assert_revision`:
  requires `current == repository_head` (computed via
  `alembic.script.ScriptDirectory`, refusing if the scripts directory
  itself has diverged heads), then walks `down_revision` from that head
  looking for `minimum_alembic_revision`, refusing on a merge point
  (non-`str` `down_revision`) or on reaching the root without finding it.
- `backend/fixtures/demo_standard_v1/manifest.json`,
  `build_fixture.py` — field/constant renamed;
  `minimum_alembic_revision = "a83c1d7e9f02"` (the earliest revision
  `SINGLE_CHOICE` existed, used by 24 seeded questions).
- `backend/tests/test_demo_data_loader.py` — `_current_repository_head()`
  helper replaces the hardcoded `alembic_version` seed, so this test can't
  develop the same staleness bug again.
- `backend/tests/unit/test_demo_data_revision_guard.py` (new, 7 tests) —
  direct coverage against a monkeypatched `ScriptDirectory`: passes at head
  and at `minimum == head`; refuses a stale database; refuses a database
  off the known head entirely; refuses before even checking the database
  when the scripts directory has diverged heads; refuses an unreachable
  minimum revision; refuses a merge point between head and the minimum
  revision. Each asserted against its specific error message, not just
  "raises something."

## Verification

| Command | Result |
|---|---|
| `node scripts/verify.mjs fast` | `VERIFY_OK` |
| Guarded PostgreSQL integration (`test_demo_data_loader.py`) | 2 passed |
| Guarded PostgreSQL integration (full) | 156 passed, 0 failed, no regressions |
| Guarded migration round trip | Clean through head `b6d4f0a17c53`, grade-override exact-schema counts unaffected |
| `tests/unit/test_demo_data_revision_guard.py` | 7 passed |
| Full unit suite | 302 passed |

## Local database reset (owner-authorized, performed once)

Target confirmed via the application's own settings resolution before
touching anything: `host=localhost port=5432 database=test_project_db`
(local-only; matches `LOCAL_DATABASE_HOSTS`).

1. **Drop/recreate**: terminated any active backends against
   `test_project_db`, `DROP DATABASE IF EXISTS`, `CREATE DATABASE`. `pgvector`
   extension check ran and was skipped (not installed on this server, same
   as the guarded `_test` database lifecycle already reports).
2. **Upgrade**: `alembic upgrade head` — clean run through all 12 revisions
   to `b6d4f0a17c53`.
3. **`plan`** (first, on the empty schema): every entity `create=N
   unchanged=0 conflict=0`, matching `expected_counts` exactly (this run
   also exercised the new minimum-revision guard against a real database
   for the first time — it passed).
4. **`apply`** (first): all entity counts written match
   `expected_counts` exactly (topics=9, materials=6, document_chunks=6,
   topic_briefs=6, exams=6, questions=60, options=144, flashcard_decks=6,
   flashcards=48, submissions=15, submission_answers=120,
   flashcard_progress=24, analytics_students=5, canonical_accounts=3);
   `DEMO_DATA_SCORE_RANGE minimum=20.0 maximum=100.0`.
5. **`verify`** (first): identical counts and score range.
6. **`apply`** (second): identical counts and score range — no error, no
   partial state.
7. **`verify`** (second): identical counts and score range.
8. **`plan`** (third, post-apply): **`create=0 conflict=0` for every one of
   the 14 entities**, `unchanged` exactly matching `expected_counts` — the
   strongest available proof of idempotency: the loader itself recognized
   every row as already present and matching, and attempted zero writes.
9. Direct confirmation that no fake governance rows were seeded:
   `audit_events` count = 0, `ai_generation_jobs` count = 0. The three
   canonical accounts (`admin@example.com`/admin,
   `teacher@example.com`/teacher, `student@example.com`/student) exist
   with the correct roles.

## Impact

- API/event/schema contract: none.
- Migration/data: none (no new migration; the reset only re-ran existing
  migrations against a fresh local schema).
- Security/ownership/tenant: none. `validate_demo_database_target`'s
  local-host and development/test-environment restriction is unchanged and
  was re-confirmed by construction (the reset target resolves through that
  same restriction).
- Dependency/toolchain: none.

## Known risks and follow-up

- The reset procedure was run manually via a one-off script, not a new
  permanent CLI command — the project has no existing tool for dropping
  and recreating the actual development database (only the guarded
  `_test` lifecycle in `backend/scripts/test_database.py`, which
  deliberately refuses to target anything but a `_test`-suffixed
  database). If this needs to become a routine operation, a small guarded
  script following that same house style (explicit local-host check,
  `--confirm` flag) would be the natural next step, but was not built here
  since the owner asked for the reset itself, not a new standing tool.

## Rollback

- Code: revert the relevant commit. No schema or migration change to roll
  back.
- Data: the local reset is reproducible by re-running the same five-step
  procedure; it has no effect on any shared or production environment.
