---
name: backend-architecture
description: Implement or review backend features in this FastAPI, SQLAlchemy 2.x, Pydantic v2, and PostgreSQL project. Use for endpoints, use cases, queries, models, schemas, authentication, authorization, uploads, migrations, audit logging, background jobs, and backend tests.
---

# Backend Architecture

Build backend changes from verified project contracts and preserve security, transaction, and data-access boundaries.

## Establish context

1. Read the root `AGENTS.md` and the nearest scoped `AGENTS.md`.
2. Read `docs/spec/CANONICAL_PROJECT_SPEC.md` and the relevant ADRs.
3. Read `docs/spec/PERMISSION_AND_OWNERSHIP_MATRIX.md` for access-control work.
4. Read `docs/spec/ERROR_AND_AUDIT_CONTRACTS.md` for errors or audited actions.
5. Inspect the existing route, schema, model, service or use case, migration, and tests before proposing a change.
6. Treat running code as authoritative when it conflicts with stale product documentation, then record any contract discrepancy.

## Preserve architectural boundaries

- Use SQLAlchemy 2.x `select()` syntax. Do not add legacy `Session.query()` calls.
- Keep transaction ownership in the application use case or unit-of-work boundary. Repositories may flush but must not independently commit business operations.
- Pass a request-scoped session through the call chain. Create a new session for background work; never reuse a request session after the request ends.
- Prevent N+1 queries with eager loading, aggregate queries, or batch loading. Never issue a database query inside an item loop without measured justification.
- Use a simple service/use-case flow for straightforward operations. Introduce richer domain or aggregate boundaries only when invariants span multiple entities.
- Enforce role, tenant, ownership, and object access in the backend. Frontend checks are presentation only.
- Return the canonical structured error contract. Do not leak stack traces, SQL, tokens, or sensitive context.
- Emit audit records for admin/teacher actions, exam changes, grading, and AI generation without storing secrets.
- Keep AI provider access behind an abstraction and capture prompt, model, token usage, latency, and context sources according to the canonical spec.

## Handle risky changes

- Request approval before changing migrations, authentication, a breaking API contract, or project architecture.
- Make every migration downgradeable and verify both upgrade and downgrade on PostgreSQL.
- Validate uploads by extension, MIME evidence, size, authorization, and tenant ownership. Use the configured local storage abstraction rather than exposing arbitrary filesystem paths.
- Preserve the 30-day retention and recovery policy where soft deletion applies.

## Verify the change

Run the narrowest relevant checks first, then the applicable suite:

- Unit tests may use SQLite only when behavior is database-agnostic.
- Query, migration, repository integration, authorization, tenant-isolation, and concurrency tests use PostgreSQL.
- Add negative permission cases, ownership cases, structured error assertions, audit assertions, and query-count coverage where relevant.
- Do not weaken an assertion merely to obtain a green build; first prove that the contract or test is wrong.
- Report test output, files changed, contract or migration impact, known risks, and manual verification in the handoff.
