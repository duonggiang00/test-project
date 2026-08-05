# Optional Containerization Path

Status: Prepared direction; Docker is not required for daily development.

## Current supported workflow

Windows remains the primary development environment. The supported local workflow is:

- Node 22 and npm 10 for the frontend.
- Python 3.12 and uv for the backend.
- A locally reachable PostgreSQL instance.
- `node scripts/verify.mjs ...` as the shared local and CI verification interface.

Do not make a Docker daemon a prerequisite for `dev`, `verify:fast`, unit tests, or ordinary agent work.

## Future service boundary

A future container profile should preserve these independently replaceable services:

| Service | Responsibility | Persistent data |
|---|---|---|
| `frontend` | Next.js server and BFF | None |
| `backend` | FastAPI application | None |
| `postgres` | Canonical relational database and pgvector | Named PostgreSQL volume |
| `migrate` | One-shot Alembic upgrade job | None |

Uploaded files remain behind the backend storage interface. A local bind mount or named volume may be used for MVP packaging, but application code must not depend directly on a container path.

## Image contracts

When images are introduced:

- Pin supported runtime major/minor versions consistently with `.nvmrc` and `backend/pyproject.toml`.
- Use `npm ci` with `frontend/package-lock.json` for frontend installs.
- Use `uv sync --frozen` with `backend/uv.lock` for backend installs.
- Use multi-stage builds so compilers, package caches, tests, and development tools are not copied into runtime images.
- Run application processes as non-root users.
- Keep environment configuration external to images.
- Never bake `.env`, tokens, document uploads, test databases, or AI logs into an image layer.

## Runtime configuration

Container configuration uses the same canonical names documented by `.env.example`:

- Backend: `DATABASE_URL`, `SECRET_KEY`, `BACKEND_CORS_ORIGINS`, and optional provider credentials.
- Frontend server/BFF: `BACKEND_API_URL`.
- Integration only: `TEST_DATABASE_URL` and optional `POSTGRES_ADMIN_DATABASE`.

The container profile may set the PostgreSQL hostname to the service name, but the daily Windows `.env` remains host-oriented. Do not add environment-specific conditionals to application business logic.

## Startup and health

The future orchestration sequence should be:

1. PostgreSQL becomes reachable and passes a readiness probe.
2. A one-shot migration job runs `alembic upgrade head` and exits successfully.
3. Backend starts and exposes a dedicated readiness endpoint that verifies required dependencies without mutating data.
4. Frontend starts only after the backend readiness contract is satisfied.

Process startup must not silently create schemas through `Base.metadata.create_all()` outside isolated tests. Migration failure must stop deployment.

## Test profile

CI may use a PostgreSQL service container while still invoking `node scripts/verify.mjs integration`. The guarded runner must target a new `_test` database and must never drop the service's admin or application database.

E2E packaging should keep two explicit profiles:

- Mocked PR E2E with deterministic BFF responses and no shared database mutation.
- Real-backend smoke E2E with an isolated PostgreSQL dataset on `main` or nightly runs.

## Deferred decisions

Do not create production-focused container manifests until the owner approves:

- Development, staging, and production topology.
- Deployment platform and registry.
- TLS termination and public routing.
- Secret manager.
- Object storage and upload persistence.
- Backup, restore, monitoring, and log retention.

## Adoption checklist

Containerization may become an implementation task when all of the following are true:

- Windows non-container verification remains green.
- CI uses the same logical verification commands.
- PostgreSQL migrations pass upgrade/downgrade/upgrade verification.
- Health/readiness contracts are implemented.
- Storage and secret boundaries are approved.
- A rollback and data-backup procedure is documented.
