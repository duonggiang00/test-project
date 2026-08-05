# ADR-0002: Transaction Boundaries and Unit of Work

Status: Accepted  
Date: 2026-08-05

## Context

Allowing individual services or repositories to commit independently makes multi-step business operations difficult to roll back and can leave partially applied state.

## Decision

- The application/use-case layer owns commit and rollback for simple use cases.
- Use an explicit Unit of Work when a use case coordinates multiple aggregates or repositories.
- Repositories perform persistence operations but do not commit independently.
- Routers translate HTTP input/output and do not own transaction-heavy business logic.
- Background work creates its own session and transaction scope.

## Consequences

- Existing service methods that commit internally will be migrated by bounded module tasks.
- Tests can assert atomic rollback at the use-case boundary.
- A Unit of Work is introduced only where aggregate coordination justifies it.

## Supersession

This ADR supersedes the 2026-08-01 memory entry that assigned transaction ownership to each service. Any future alternative must define atomicity and rollback behavior explicitly.

