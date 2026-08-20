# Change Contract: DATA-DEMO-002 Minimum-Revision Dataset Compatibility

Risk level: L2
Owner: Primary implementation agent
Approval required: No (schema-compatibility check and local-only data-lifecycle
operation; no application behavior, migration, or permission change)
Approval evidence: The project owner directed this work explicitly in
conversation on 2026-08-19/20, including explicit authorization to drop and
recreate the local development database as part of the reset workflow.

## Scope

In scope:

- Replace `demo-standard-v1`'s manifest `alembic_head` exact pin (which had
  gone stale: it still named `f9f952e6df1a` after three later heads shipped)
  with `minimum_alembic_revision`, and change
  `DemoDataManager._assert_revision` to check (a) the live database sits at
  the repository's actual current head, computed live from the Alembic
  scripts directory, and (b) that head is a linear descendant of the
  manifest's minimum revision, with no branch/merge point in between.
- Fix the one existing test that had the same staleness bug (a hardcoded
  `alembic_version` seed) so it computes the real head the same way the
  guard does.
- Add direct unit coverage for the new guard's failure paths (stale,
  diverged repository history, unreachable minimum revision, merge point).
- Perform, once, the owner-authorized local database reset: confirm the
  exact host/database target, drop and recreate the local development
  database (`test_project_db` at `localhost:5432`), upgrade to head
  (`b6d4f0a17c53`), and run `plan → apply → verify → apply → verify` to
  prove the dataset loads cleanly and idempotently against a fresh schema.

Out of scope:

- Any change to fixture content, deterministic UUIDv5 identities, or
  `expected_counts` — all preserved exactly.
- Seeding any audit event or AI-generation-review row — confirmed absent
  (`audit_events` and `ai_generation_jobs` are empty after the reset).
- Any change to `validate_demo_database_target` (host/environment
  restriction) — already correct and untouched.

## Behavior

- Before: the manifest pinned an exact Alembic revision that had already
  gone stale three heads ago; a fresh `plan`/`apply` against current head
  would have failed with "database is not at the fixture's required
  Alembic head" had anyone actually run it, since nothing forced the pin
  to move forward when unrelated migrations shipped.
- After: the manifest names the earliest revision the fixture's content
  actually requires (`a83c1d7e9f02`, where `SINGLE_CHOICE` — used by 24
  seeded questions — was added); the loader accepts any current repository
  head that descends linearly from it, so future additive migrations do
  not require touching the fixture again, while a genuine incompatibility
  (a merge point, or a minimum revision no longer in the repo's history)
  is still refused.
- Preserved invariants: fixture content, IDs, and counts are byte-identical
  to before. `validate_demo_database_target`'s local-host and
  development/test-environment restriction is unchanged.

## Expected files and contracts

- `backend/app/demo_data/fixture.py` — `DemoManifest.minimum_alembic_revision`
  replaces `alembic_head`.
- `backend/app/demo_data/loader.py` — `DemoDataManager._assert_revision`
  rewritten per the two-check design above.
- `backend/fixtures/demo_standard_v1/manifest.json`,
  `backend/fixtures/demo_standard_v1/build_fixture.py` — field/constant
  renamed; value changed to `a83c1d7e9f02`.
- `backend/tests/test_demo_data_loader.py` — `alembic_version` seed computed
  live instead of hardcoded.
- `backend/tests/unit/test_demo_data_revision_guard.py` (new) — direct
  coverage of the guard's accept/refuse paths against a monkeypatched
  `ScriptDirectory`.

No API, schema, or migration changes. No new dependency.

## Verification contract

- `node scripts/verify.mjs fast`.
- Guarded PostgreSQL integration suite (`uv run --frozen python -m
  scripts.run_integration` from `backend/`).
- Guarded migration round trip (`uv run --frozen python -m
  scripts.run_migration_roundtrip` from `backend/`) — unaffected by this
  change, re-run to confirm.
- New unit suite (`tests/unit/test_demo_data_revision_guard.py`) covering
  every refusal path.
- The local reset procedure itself, executed once and recorded in the
  handoff: confirm target, drop/recreate, upgrade to head,
  `plan → apply → verify → apply → verify`, with the second `plan` showing
  `create=0 conflict=0` for every entity and `audit_events`/
  `ai_generation_jobs` confirmed empty.

## Rollback

- Code: revert the relevant commit. No migration or schema change to roll
  back.
- Data: the local database reset is local-only and reproducible by
  re-running the same procedure; it has no effect on any shared or
  production environment (the loader refuses non-local hosts by
  construction).

## Assumptions and drift

- Verified assumption: every migration between `a83c1d7e9f02` and the
  current head (`f9f952e6df1a`, `1dfa8dca16d5`, `c4e1a70b58d9`,
  `e7b21c9d4a83`, `b6d4f0a17c53`) is additive and does not change the
  meaning of any column the fixture writes — proven empirically by the
  fixture loading and verifying cleanly against current head without any
  fixture content change.
- No SPEC_DRIFT introduced or resolved by this contract.
