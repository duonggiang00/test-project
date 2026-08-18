# Executable Architecture Guards

Run:

```text
node scripts/architecture-guard.mjs check
node scripts/architecture-guard.mjs fixtures
```

The canonical fast gate runs `check`. The fixture command proves compliant examples produce no findings and violation examples exercise every configured rule.

Ruff also runs its syntax/name-error baseline across `backend/app`, `backend/scripts`, and `backend/tests`. Mypy checks the explicitly typed configuration, security, and safe test-runner modules. Expand the mypy `files` list as modules acquire trustworthy annotations; do not add broad ignores to claim coverage.

## Enforced rule families

- Backend: new `Session.query()`, `datetime.utcnow()`, bare `except`, raw exception messages, queries inside loops, request sessions passed to background tasks, invalid router/model/service imports, and `openai` SDK imports outside `app/ai/openrouter_adapter.py`.
- Frontend: direct backend-origin calls outside BFF handlers, fetching inside UI components, token local storage, server collections in Zustand, reload-based mutation handling, and remote fonts.
- Contracts: backend decorator and frontend transport trailing slashes.
- Design: non-black/white Tailwind color tokens and color literals.

`config/architecture-guard-baseline.json` records 247 existing fingerprints. Existing debt may be removed, but a new fingerprint fails. Matching uses rule + file + normalized source snippet, so moving line numbers does not create noise while copying or introducing a violation still exceeds the recorded allowance.

Never regenerate the baseline merely to make the gate green. Baseline changes require a reviewed explanation of every added allowance. The current counts are debt inventory, not approved examples.

The fast gate also compares runtime FastAPI OpenAPI against `docs/generated/openapi.json`. Regenerate only after reviewing the complete contract diff; breaking API changes retain their explicit approval boundary.

`config/database-model-signature.json` binds the runtime SQLAlchemy model hash to the Alembic head set. The generator refuses a changed model hash when heads are unchanged, so a missing migration cannot be hidden by regenerating the file. Migration edits still require approval and downgrade evidence.
