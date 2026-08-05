# Generated Project Inventory

The generated inventory is stored at `docs/generated/project-inventory.json`. Do not edit it manually.

Commands:

```text
node scripts/project-inventory.mjs generate
node scripts/project-inventory.mjs check
node scripts/project-inventory.mjs context exam
```

The backend section comes from registered SQLAlchemy mappers, imported Pydantic models, FastAPI `APIRoute` objects, Alembic heads, and Python AST test discovery. The frontend section deterministically scans App Router pages/layouts, BFF handlers, hooks, services, and test files.

Provenance includes:

- Generator version.
- Source commit and commit timestamp at generation time.
- SHA-256 over every relevant source/config/generator file.
- Relevant-file count.
- Alembic heads.

The source-tree hash is the freshness authority because a generated file cannot contain the hash of the commit that contains itself. Documentation-only commits do not invalidate technical inventory. Any relevant backend/frontend/test/generator change does.

Coverage providers and commands are recorded, but percentage fields remain `null` until `TEST-001` measures reproducible baselines. Agents must not interpret `null` as zero coverage or as a passing baseline.

The `context` command verifies freshness before returning matches. Use a domain term such as `exam`, `material`, `student`, or `auth`; do not copy route/model lists into manual project-state documents.
