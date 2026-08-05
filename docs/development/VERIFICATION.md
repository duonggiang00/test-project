# Verification Entry Points

Use Node 22, npm 10, Python 3.12, and uv. Install locked dependencies before verification:

```powershell
cd frontend
npm ci
cd ..
cd backend
uv sync --frozen
cd ..
```

The shared command is cross-platform and does not depend on the legacy batch file:

```text
node scripts/verify.mjs env
node scripts/verify.mjs fast
node scripts/verify.mjs backend
node scripts/verify.mjs frontend
node scripts/verify.mjs integration
node scripts/verify.mjs migration
node scripts/verify.mjs e2e
node scripts/verify.mjs all
```

## Mode contracts

| Mode | Contract |
|---|---|
| `env` | Validate canonical, non-secret `.env.example` keys |
| `fast` | Env contract, backend unit tests, frontend lint/unit/build |
| `backend` | Backend unit tests followed by the guarded PostgreSQL integration lifecycle |
| `frontend` | Frontend lint, unit tests, and production build |
| `integration` | Create a new local `_test` PostgreSQL database, run integration tests, and drop it in `finally` |
| `migration` | Create an isolated database and run Alembic upgrade → downgrade → upgrade before cleanup |
| `e2e` | Existing Playwright flow against the configured application |
| `all` | Backend, frontend, and E2E checks in sequence |

The production build explicitly uses Next.js' documented `--webpack` mode because the default Turbopack build did not complete within the five-minute fast-gate budget on the official Windows environment.

## PostgreSQL isolation

The integration entry point derives `<development_database>_test` unless `TEST_DATABASE_URL` is supplied. The target must be on `localhost`, must end in `_test`, must differ from the development and admin databases, and must not already exist. The runner refuses unsafe targets and never prints credentials.

When the PostgreSQL server provides pgvector, the lifecycle enables the `vector` extension in the new test database. A local server without the extension records an explicit skip; tests that actually require vector behavior must then fail rather than claim coverage.

Use the guarded status command when diagnosing an interrupted run:

```text
cd backend
uv run --frozen python -m scripts.test_database status
uv run --frozen python -m scripts.test_database drop
```

The explicit `drop` command still enforces the local-host and `_test` name guards. Inspect its sanitized target output before using it.

The migration mode uses the same lifecycle and stops at the first failed stage. A failure is never bypassed by stamping the database or editing a migration during verification.

The current E2E suite is not fully mocked because global authentication and the student flow require a live backend. Keep mocked PR E2E and real-backend E2E separate when implementing `TEST-006` and `CI-005`.

The verification process stops on the first failure and preserves the underlying command's exit code. A failed command is evidence of a gate failure, not an orchestration failure.

The repository uses the tracked `.githooks/pre-commit` hook and local `core.hooksPath=.githooks`. It runs the same canonical fast gate; frontend-local Husky hooks are intentionally not used because frontend is not a nested Git repository.
