# Handoff: TOOL-PYTEST-CACHE-001 and SEC-CSP-001

Status: DONE
Risk level: L2 — workflow reliability and browser security policy

## Outcome

- Summary: The canonical coverage runner no longer depends on a readable pytest cache, and the production CSP now removes unused remote origins plus development-only `unsafe-eval` while preserving static App Router output.
- Requirements/task IDs: `TOOL-PYTEST-CACHE-001`, `SEC-CSP-001`

## Files changed

- `backend/scripts/run_coverage.py` — creates the report directory and disables pytest's cache provider in both coverage phases.
- `backend/tests/unit/test_run_coverage.py` — verifies exact cache-independent arguments, report-directory creation, phase ordering, and exit propagation.
- `frontend/src/lib/content-security-policy.ts` — builds the environment-aware CSP from a testable pure function.
- `frontend/src/lib/content-security-policy.test.ts` — locks the production allowlist and development-only exception.
- `frontend/next.config.ts` — applies the generated policy to every route.
- `docs/plans/WORKFLOW-COVERAGE-CSP-001_CHANGE_CONTRACT.md` — records scope, invariants, verification, and rollback.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — records both completions and the six-item resumed backlog.
- `docs/handoffs/WORKFLOW-COVERAGE-CSP-001.md` — records verification, independent review, residual risk, and rollback.
- `docs/generated/project-inventory.json` — regenerated after the source/test changes.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| Focused coverage-runner unit tests | 0 | 4 | 4 | 0 | 0 | Both pytest phases include `-p no:cacheprovider`; reports are created; phase failures stop and propagate. |
| Focused CSP unit tests | 0 | 2 | 2 | 0 | 0 | Production allowlist and development-only `unsafe-eval` behavior pass. |
| `node scripts/verify.mjs coverage` | 0 | 672 | 672 | 0 | 0 | Backend: 352 unit/contract + 171 PostgreSQL at 90.57%; frontend: 149 at 61.25%; policy reports `COVERAGE_OK`; managed database dropped. |
| `node scripts/verify.mjs fast` | 0 | 501 tests + build | 501 | 0 | 0 | All guards, lint/type checks, 328 backend unit, 24 contract, 65 frontend unit, 84 component, and 23-page production build pass. |
| `node scripts/verify.mjs e2e-mocked` | 0 | 28 | 28 | 0 | 0 | Chromium, Firefox, WebKit, and mobile Chrome pass; owner/flake policy reports `PLAYWRIGHT_POLICY_OK`. |
| Scoped Ruff and ESLint | 0 | changed files | all | 0 | 0 | No findings. |

## Impact

- API/event/schema contract: None.
- Migration/data: None. Coverage creates and drops only the guarded `_test` PostgreSQL database.
- Security/ownership/tenant: Production CSP is narrowed to same-origin application transport and local/blob/data assets. Backend authorization and tenant isolation are unchanged.
- Dependency/toolchain: No dependency or lockfile change.

## Manual evidence

- Scenario: Start the final production build on `127.0.0.1:3200` and request `/login`.
- Result: HTTP 200 with `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self';`. Forbidden production token/origin count was zero.
- Scenario: Start the development server on `127.0.0.1:3201` and request `/login` after compilation.
- Result: HTTP 200 with the same narrowed origins and protections; only `script-src` additionally contains development-required `unsafe-eval`. Forbidden external-origin count was zero.
- Screenshot/trace: Mocked E2E completed without failures, retries, or flakes; artifacts are ignored and not staged.

## Risks and follow-up

- Known risks: `unsafe-inline` remains for scripts/styles to preserve current static rendering. A nonce policy would require dynamic rendering and is a separate architecture decision.
- Unverified items: None within the approved scope.
- Independent review: L2 sign-off granted with no P1/P2. P3-1 was closed by the development HTTP capture; P3-2 was closed by adding the task rows, completion ledger, and resumed backlog to the canonical tracker.
- Follow-up tasks: Proceed to the bounded language/coverage waves. Nonce-based CSP remains a separately approved architecture decision if later required.

## Rollback

- Code: Revert the scoped commit. Restore only a verified required CSP origin/directive, with a regression test, if production evidence finds a blocked dependency.
- Data: None.
