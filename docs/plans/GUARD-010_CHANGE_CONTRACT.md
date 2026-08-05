# Change Contract: GUARD-010 — SQLAlchemy/Alembic Drift Guard

Risk level: L1 gate; migration changes remain approval-gated
Owner: Primary Codex agent
Approval required: No for the gate

## Intent

Bind the deterministic runtime SQLAlchemy model signature to the current Alembic head set. A model signature change with unchanged migration heads fails and cannot be regenerated away.

## Behavior

- Model change + unchanged heads: fail as missing migration.
- Changed heads: require reviewed signature regeneration.
- Unchanged models/heads: pass.
- The guard does not repair or rewrite migration history and does not bypass the blocked migration round trip.
