# Backend Test Rules

Apply this file to changes under `backend/tests/`.

- Test observable contracts and invariants rather than implementation details.
- Do not change or remove an assertion merely to make a failure pass. First prove that the test or approved contract is wrong.
- Use realistic, deterministic English fixtures. Do not depend on shared developer data or test order.
- Use SQLite only for suitable unit tests. Run query, migration, constraint, and integration behavior against PostgreSQL.
- Cover success, validation, authentication, ownership, state-conflict, and sanitized-failure paths as applicable.
- For sensitive endpoints, include anonymous, student, owner teacher, non-owner teacher, and admin cases.
- Query-budget tests compare representative small and larger datasets and fail when query count scales per row.
- Migration tests verify upgrade, downgrade, and upgrade again without an existing developer database.
- Mock only external boundaries when the boundary itself is not under test.
- Report collected, passed, failed, and skipped counts. A required PostgreSQL test that did not run is not a pass.

