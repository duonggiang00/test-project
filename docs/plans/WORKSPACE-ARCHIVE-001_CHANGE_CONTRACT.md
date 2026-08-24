# Change Contract: WORKSPACE-ARCHIVE-001 — Archive non-runtime workspace artifacts

Risk level: L1  
Owner: Codex  
Approval evidence: The project owner explicitly requested investigation, cleanup, and archival on 2026-08-20.

## Scope

- Archive local report-generation inputs/outputs, the reconstructible `1713f77` report snapshot, temporary report/demo artifacts, unused pig-logo experiments, and the obsolete local pnpm store.
- Archive the twelve tracked, unreferenced ad-hoc Python files located directly under `backend/`. These legacy utilities bypass current migration/data-safety/test conventions and have official replacements under Alembic, `backend/scripts/`, generated inventory, or `backend/tests/`.
- Preserve application code, active tests, canonical specifications, engineering contracts/handoffs, `.claude`, local environments, uploads, databases, and current frontend/backend build state.
- Store moved content under `.legacy-archive/non-runtime-artifacts-20260820/`, which is already Git-ignored and recoverable.

## Impact

- Runtime/API/schema/migration/security impact: None.
- Git-tracked source impact: Only this contract and a historical note in the report contract.
- Recovery: Move an archived item back to its recorded original path. The report source snapshot can also be recreated with `git archive 1713f77` because commit `1713f77d1307c40e7c00c3955a00b3c3d4b25515` exists locally.

## Archived backend Python utilities

- Manual schema/data mutation: `add_enum.py`, `cleanup.py`, `clear_mock_data.py`, `remove_e2e_data.py`, `remove_mock_exams.py`.
- Legacy inspection/seeding: `check_db.py`, `create_test_users.py`, `seed_detailed_data.py`.
- Obsolete generated-context/ad-hoc probes: `generate_rag_specs.py`, `test_ai.py`, `test_client.py`, `test_pwd.py`.
- Replacements: Alembic revisions and migration round-trip runner; `python -m scripts.seed_demo_data`; `python -m scripts.run_integration`; `scripts/project-inventory.mjs`; formal pytest contract/unit/integration suites.

## Verification

- Resolve every source and destination to an absolute path before moving.
- Refuse any source outside `D:\projects\test-project` and any destination outside the named archive root.
- Confirm all original top-level candidates are absent and every mapped archive target exists.
- Confirm the scoped Git diff contains no application-code mutation from this cleanup.
