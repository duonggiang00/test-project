# Backend Agent Rules

Apply this file to changes under `backend/` together with the workspace `AGENTS.md`.

## Architecture

- Keep HTTP parsing and response mapping in FastAPI routers; keep business decisions in application use cases/services.
- Use SQLAlchemy 2.x `select()` for new or migrated queries. Do not introduce `Session.query()`.
- Let the use-case layer own commit/rollback for simple operations. Use an explicit Unit of Work for multi-aggregate operations.
- Repositories and helpers must not commit independently.
- Background work creates its own session and transaction; never reuse a request-scoped session.
- Use timezone-aware UTC timestamps.

## Contracts and validation

- Use Pydantic v2 models with strict request/response types.
- Keep request schemas separate from persisted models when permissions or writable fields differ.
- Emit the canonical `error_code`, object `details`, and `request_id` error shape.
- Do not expose raw exception strings, SQL, filesystem paths, provider errors, or secrets.
- Do not add trailing slashes to endpoint decorators.
- Treat OpenAPI changes as contracts. Breaking changes require approval.

## Authorization and ownership

- Backend enforcement is mandatory for every sensitive read and mutation.
- Use named policies from `docs/spec/PERMISSION_AND_OWNERSHIP_MATRIX.md`; avoid scattered role comparisons.
- Scope queries by ownership/visibility where practical so inaccessible records do not leak existence.
- Apply the same boundary to list, detail, bulk, background, and export paths.
- Admin override must be explicit and auditable.
- Non-owner teacher access is denied in the target policy.

## Database and performance

- PostgreSQL is authoritative for query, constraint, migration, and integration behavior.
- SQLite is allowed only for suitable isolated unit tests.
- Prevent N+1 queries with a query shape appropriate to cardinality: eager loading, projections, aggregates, or bulk queries.
- Do not issue database queries inside item loops.
- Add a query-budget test when changing important list/detail relationship loading.
- Model changes require an Alembic migration with upgrade/downgrade/upgrade verification.

## Audit, deletion, and files

- Emit required audit events atomically with successful business changes when stored in the same database.
- Do not log secrets, tokens, raw sensitive documents, or unapproved raw AI content.
- Default reads exclude soft-deleted data.
- Respect the approved 30-day recovery window; do not permanently purge submissions, grades, or sensitive AI logs until retention is approved.
- File uploads accept only PDF, DOCX, PPTX, and TXT up to 50 MB and must validate extension, MIME, signature, path safety, and owner/admin access.

## Verification

- Pure logic: focused unit tests.
- Use case/endpoint: contract tests including negative authorization cases.
- Query/migration/database behavior: PostgreSQL integration tests.
- Migration: upgrade, downgrade, upgrade again.
- Security-sensitive work: independent review and IDOR/cross-owner tests.

Read `backend/tests/AGENTS.md` before changing backend tests.

