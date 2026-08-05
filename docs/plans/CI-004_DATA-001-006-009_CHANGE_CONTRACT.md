# Change Contract: CI-004 and DATA-001–006/009 — Migration and Data Lifecycle

Risk level: L3 migration, audit, soft delete, retention, and purge  
Owner: Primary implementation agent after approval  
Independent review: Migration/data and security reviewers required  
Approval required: Yes  
Approval evidence: Pending in `REMAINING_HIGH_RISK_APPROVAL_PACKET.md`

## Scope

In scope:

- Repair the fresh-database failure in initial revision `27f1dff6a48f`.
- Add the canonical append-only audit event and atomic audit-writing service.
- Add soft-delete/default-read/restore behavior to governed aggregate roots.
- Implement 30-day recovery and admin-only, dry-run-first bounded purge only for
  record classes with an approved permanent-retention rule.
- Apply owner/admin lifecycle behavior to local material files without losing
  retryability when database and filesystem operations fail separately.

Out of scope:

- Running or downgrading migrations on shared/non-test data, restoring row data
  through schema downgrade, legal retention claims, production scheduling, and
  permanent deletion of submissions/grades under the MVP policy.

## Verified current behavior and drift

- Fresh upgrade fails because `27f1dff6a48f` unconditionally drops indexes from
  a legacy `user` table that does not exist on a fresh database.
- `backend/scripts/run_migration_roundtrip.py` already creates a guarded `_test`
  database and runs upgrade/downgrade/upgrade with `finally` cleanup.
- No canonical audit table/service, soft-delete mixin, restore service, purge
  runner, or retention registry exists.
- Services generally commit independently. Required successful actions cannot
  become auditable merely through a logging side effect; the business change
  and audit row must share a transaction.
- Local file storage is abstracted, but current material deletion physically
  removes the row/file instead of following an owner-scoped recovery lifecycle.

## Target behavior and invariants

### Migration repair

- In `27f1dff6a48f.upgrade`, inspect PostgreSQL for the legacy `user` table. If it
  exists, drop the table once and let PostgreSQL drop its indexes; otherwise do
  nothing. Remove both unconditional legacy index drops.
- Drop the legacy PostgreSQL `role` enum with `create_type=False` and
  `checkfirst=True` after the conditional table removal so a
  downgrade-to-base/second-upgrade does not leave an orphan type.
- Keep downgrade schema behavior sufficient for a fresh
  upgrade/downgrade/upgrade round trip. Schema downgrade does not promise row
  restoration.

### Audit core

- `audit_events` contains an immutable event ID, timezone-aware UTC occurrence,
  request/job ID, actor ID/role or explicit system actor, stable action,
  entity type/ID/owner, outcome, safe JSONB changes, and safe JSONB metadata.
- `AuditService.record(db, event)` adds/flushes but never commits. A required
  successful business action owns the transaction; audit failure prevents a
  silent unaudited success.
- Application code exposes no update/delete operation for individual events.
  Full reads are admin-only; future owner-scoped teacher reads use the same
  policy layer as business data.
- Secrets, tokens, uploaded content, raw provider errors, and unrestricted raw
  prompts/context never enter the core audit JSON.
- Actor/entity identifiers are denormalized without cascading foreign keys so
  audit history survives business-record lifecycle changes. Use a non-reserved
  Python attribute such as `event_metadata` for the database `metadata` column.
- Request-ID middleware and explicit job correlation populate every event.

### Soft delete and purge

- Governed roots use timezone-aware `deleted_at` and `deleted_by_id`; default
  queries exclude deleted rows. Restore clears deletion state only within 30
  days and only for admin or the owning teacher.
- Permanent purge is admin-only, explicit, bounded, dry-run capable, idempotent,
  and audited. It never treats skipped/unclassified data as eligible.
- At the exact boundary, purge is eligible when `deleted_at <= now - 30 days`;
  restore is eligible only while `deleted_at > now - 30 days`. Batches use the
  deterministic order `(deleted_at, id)`.
- Submissions and grades are retained indefinitely in the MVP after soft delete;
  permanent purge remains disabled pending a later educational-record ADR.
- Restricted raw AI prompt/retrieved-context payloads expire 30 days after job
  completion. Redacted metadata, source IDs/citations, reviewer, and outcome
  remain while the parent record exists; no automated MVP purge applies.
- File purge uses a persistent pending/completed retry state and reversible
  `FileStorage` quarantine. Record eligibility/request audit, atomically move the
  file to quarantine, hard-delete eligible metadata plus completion audit in a
  database transaction, then finalize physical deletion after commit. Database
  rollback restores quarantine; interruption leaves a recoverable job/receipt
  for deterministic retry rather than a missing active file or false success.
- Apply soft deletion first to current delete-capable roots: User, Topic, Exam,
  standalone/owned Question, and StudyMaterial. Normal session reads use a
  default loader criterion; restore/purge paths require an explicit narrowly
  scoped `include_deleted` execution option.
- Purge is allowlisted, not generic. Initially only material data proven not to
  cascade into protected educational records is eligible. User, Exam, Question,
  and unsafe Topic purge remains blocked because current foreign keys can delete
  submissions, answers/grades, or flashcard progress.

## Expected files and contracts

- `backend/alembic/versions/27f1dff6a48f_initial_migration.py` plus new additive
  audit/soft-delete/lifecycle revisions after the repaired head.
- New audit, deletion/retention policy, purge-job/service modules; model exports;
  affected schemas and admin/owner endpoints.
- Existing admin, auth, topic, material, exam, question, grading, AI, restore,
  and purge use cases instrumented incrementally without repository-level commit.
- Local file storage remains the provider boundary; no object-store dependency.
- `main.py` currently mounts all material files publicly and material responses
  expose internal `file_path`. DATA-009 replaces this with an authenticated
  owner/admin `/materials/{id}/download` boundary, limits public static mounting
  to approved avatar assets, and removes/deprecates internal material paths.
  This behavior/API change is explicitly part of Batch D approval.

API/event impact:

- Audit event names and fields follow `ERROR_AND_AUDIT_CONTRACTS.md`.
- Restore/purge APIs are additive. Expected errors use the canonical structured
  error envelope. Any breaking path or response change returns for approval.

## Required order

1. Repair CI-004 and prove the existing full migration chain round trip.
   If a later legacy revision then fails (for example on an unnamed constraint),
   diagnose its real PostgreSQL state and update this contract; never weaken the
   round-trip runner or skip a revision to obtain green output.
2. Add DATA-001 audit core and request/job correlation.
3. Allow SEC admin override/auth revocation work to consume the audit boundary.
4. Add DATA-003 soft-delete fields/query policy in small aggregate-group
   migrations, followed by DATA-004 restore.
5. Instrument DATA-002 actions as each affected use case adopts transaction
   ownership; do not create a global ORM hook without actor context.
6. Record the approved DATA-006 retention registry.
7. Add DATA-005 bounded purge and DATA-009 file lifecycle.
8. Independent migration/security review and completion audit.

## Verification contract

- Guarded fresh upgrade, downgrade, second upgrade, head verification, model
  signature, absence of legacy `user`/`role` at head, and confirmed `_test`
  database absence. The runner gains exact PostgreSQL schema assertions rather
  than trusting process exit alone.
- Audit schema constraints; one success event per required action; rollback leaves
  no false success event; audit failure prevents required unaudited success.
- Redaction fixtures prove tokens/secrets/raw documents do not serialize.
- PostgreSQL default-read exclusion, explicit include-deleted admin path,
  owner/admin restore, non-owner denial, 30-day boundary, timezone, dry-run,
  batch/idempotency/concurrency, and retry tests.
- File failure injection for database failure, storage failure, retry, and final
  cleanup; authenticated download; public material URL denial; quarantine
  rollback; no cross-owner path access.
- Fast, integration, migration, architecture, OpenAPI, and changed-code coverage
  gates plus independent migration/security review.

## Rollback

- Revert application behavior while retaining additive audit/deletion columns.
- Disable purge scheduling first. Retry/inspect pending file purges before code
  rollback; never reclassify them as completed without storage evidence.
- Do not downgrade shared/live data as an application rollback mechanism.
- A soft-delete-column downgrade must refuse while deleted rows exist unless an
  explicit data-preservation export/reclassification has been approved; losing
  logical deletion state is destructive.
