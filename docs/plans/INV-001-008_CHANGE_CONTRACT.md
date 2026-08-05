# Change Contract: INV-001 through INV-008 — Generated Project Inventory

Risk level: L1
Owner: Primary Codex agent
Approval required: No
Approval evidence: The owner approved execution of the canonical optimization plan.

## Scope

- In scope:
  - Generate SQLAlchemy model/relationship, Pydantic schema, FastAPI route/dependency, Next.js route/layout, hook, service, and test inventories.
  - Record coverage-tool metadata without inventing an unmeasured baseline.
  - Attach generator version, source commit, source commit timestamp, source-tree hash, and Alembic heads.
  - Provide Windows-friendly `generate`, `check`, and feature `context` commands.
  - Fail the fast gate when relevant source changes make the generated inventory stale.
- Out of scope:
  - Measuring coverage baselines (`TEST-001`).
  - Changing application behavior, API contracts, models, schemas, routes, or tests.
  - Treating regex/static output as proof of runtime behavior when runtime introspection is available.

## Behavior

- Before:
  - Agents manually search the repository and may rely on stale snapshots.
  - No machine-verifiable inventory provenance or stale check exists.
- After:
  - Backend contracts are introspected from registered runtime objects.
  - Frontend routes/data-layer files and test files are deterministically scanned.
  - `docs/generated/project-inventory.json` is reproducible and checked by the fast gate.
  - Feature context refuses stale inventory and returns only matching technical entries.
- Preserved invariants:
  - Current code remains the source of truth.
  - Generated inventory is evidence, not authorization to change contracts.
  - No secrets or environment values enter the inventory.

## Expected files and contracts

- Files/modules:
  - Backend runtime inventory emitter.
  - Root cross-platform inventory generator/check/context command.
  - Generated JSON artifact and inventory documentation.
  - Fast verification and CI integration.
  - Canonical agent-policy clarification and program tracker.
- API/event/schema impact: None.
- Migration/data impact: None.
- Security/ownership/tenant impact: None.

## Verification contract

- Targeted tests: Exercise generate, check, stale detection, and feature context.
- Static/type checks: Python compile and Node syntax checks.
- Integration/PostgreSQL checks: Not required; runtime introspection must not connect to the database.
- Build/E2E/visual checks: Fast gate must remain green.
- Manual verification: Compare reported counts with direct filesystem/runtime queries.

## Rollback

- Code rollback: Revert generator, generated artifact, verification step, and docs.
- Data rollback: Not applicable.

## Assumptions and drift

- Verified assumptions:
  - Root Git now has a real baseline commit.
  - Backend imports and frontend filesystem scanning can run without database access.
- Unresolved assumptions:
  - Coverage percentages remain intentionally absent until `TEST-001`.
- SPEC_DRIFT: None identified at contract creation.
