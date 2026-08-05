# ADR-0001: PostgreSQL and SQLAlchemy 2.x

Status: Accepted  
Date: 2026-08-05

## Context

The repository has mixed SQLite/PostgreSQL assumptions and legacy ORM patterns. Production-oriented query, constraint, and migration behavior must be tested against the official database.

## Decision

- PostgreSQL is the official database.
- SQLite is permitted only for isolated unit tests that do not depend on PostgreSQL behavior.
- Query, migration, and integration tests run against PostgreSQL.
- New or migrated data access uses SQLAlchemy 2.x `select()` syntax.
- New `Session.query()` usage is prohibited and will become a CI-enforced rule.

## Consequences

- Local and CI workflows need an isolated PostgreSQL integration profile.
- Existing legacy queries may be migrated incrementally rather than in a single rewrite.
- Tests relying on PostgreSQL semantics cannot claim verification when run only on SQLite.

## Supersession

This ADR supersedes project guidance that treats SQLite as the primary application database. A later ADR must explicitly supersede this decision to change the official database or ORM style.

