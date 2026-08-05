# ADR-0007: Source of Truth and Specification Drift

Status: Accepted  
Date: 2026-08-05

## Context

Historical PRDs, agent memory, workflow documents, and current code contain conflicting facts. Timestamp-based trust alone can make a fresh-looking snapshot inaccurate.

## Decision

Use this authority order:

1. Executable application behavior and contracts in current code.
2. Accepted ADRs.
3. Approved canonical specification.
4. Scoped agent instructions and workflows.
5. Commit-bound generated inventory.
6. Historical documents.

When code and historical documentation differ, record `SPEC_DRIFT`. Current code is the operational baseline but is not automatically declared correct. Authentication, authorization, migrations, breaking contracts, and major behavior changes require owner approval.

Technical inventory is generated from code and tied to a commit SHA and Alembic head. It is not trusted merely because it is less than a fixed number of days old.

## Consequences

- Historical snapshots cannot override live evidence.
- Accepted decisions must be marked superseded rather than contradicted in place.
- Agents must report unresolved drift and unverified assumptions.

## Supersession

This ADR supersedes the age-only trust model in the previous project memory protocol.

