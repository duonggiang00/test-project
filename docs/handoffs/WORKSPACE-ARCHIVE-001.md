# Handoff: WORKSPACE-ARCHIVE-001 — Archive non-runtime workspace artifacts

Status: DONE  
Risk level: L1

## Outcome

- Summary: The active workspace now contains product code, formal tests, current engineering documentation, and active tool configuration only. Report-generation artifacts and clearly obsolete/ad-hoc utilities were moved to the recoverable ignored archive `.legacy-archive/non-runtime-artifacts-20260820/`.
- Requirements/task IDs: `WORKSPACE-ARCHIVE-001`

## Files changed

- `docs/plans/WORKSPACE-ARCHIVE-001_CHANGE_CONTRACT.md` — exact archive scope, replacements, recovery, and verification.
- `docs/plans/REPORT_PLAYSTUDY_CHANGE_CONTRACT.md` — records the new report-artifact location.
- `docs/plans/DATA-DEMO-001_CHANGE_CONTRACT.md` — makes `scripts.seed_demo_data` the only active demo-seed entry point and records the retired wrapper.
- `docs/plans/AGENT_WORKFLOW_OPTIMIZATION_PLAN.md` — completion evidence.
- `backend/add_enum.py`, `check_db.py`, `cleanup.py`, `clear_mock_data.py`, `create_test_users.py`, `generate_rag_specs.py`, `remove_e2e_data.py`, `remove_mock_exams.py`, `seed_detailed_data.py`, `test_ai.py`, `test_client.py`, `test_pwd.py` — removed from the active tracked tree and preserved under `legacy-backend-scripts/` in the local archive.
- `.legacy-archive/non-runtime-artifacts-20260820/README.md` — local archive inventory and recovery instructions.

## Verification

| Command | Exit | Collected | Passed | Failed | Skipped | Relevant result |
|---|---:|---:|---:|---:|---:|---|
| `uv run --frozen pytest --collect-only -q` | 0 | 476 | 476 | 0 | 0 | Formal test discovery is intact |
| `uv run --frozen ruff check app scripts tests` | 0 | — | — | 0 | — | `All checks passed!` |
| Executable-reference scan excluding docs/archive | 0 | 12 names | 12 | 0 | 0 | `NO_EXECUTABLE_REFERENCES_TO_ARCHIVED_PYTHON` |
| Active loose-Python count | 0 | — | — | — | — | `backend/*.py` count is `0` |
| Validated move/readback | 0 | 24 mapped items | 24 | 0 | 0 | Original paths absent; archive destinations present |

## Impact

- API/event/schema contract: None.
- Migration/data: No migration or database mutation. The unsafe manual enum/data scripts were retired, not executed.
- Security/ownership/tenant: No product behavior change. Fixed-password and broad-delete ad-hoc scripts are no longer discoverable in the active backend root.
- Dependency/toolchain: Canonical npm, uv, Alembic, pytest, generated inventory, and guarded database runners remain unchanged.

## Manual evidence

- Scenario: Inspect active top-level workspace and direct `backend/*.py` files after the move.
- Result: Report output/template/logo/tmp clutter is absent from the active root; all twelve loose backend Python files are absent; `.claude`, source, tests, specifications, current contracts, local environments, uploads, and databases remain in place.
- Remaining Python outside the four backend code/test/migration/script roots is intentional: two positive/negative architecture-guard fixtures and `backend/fixtures/demo_standard_v1/build_fixture.py`, the versioned demo-dataset asset builder.
- Archive: `.legacy-archive/non-runtime-artifacts-20260820/` contains the full mapping and README.

## Risks and follow-up

- Known risks: `.legacy-archive/` is intentionally Git-ignored, so it is a local recovery mechanism rather than a remote source archive. Former tracked scripts remain recoverable from Git history; the report snapshot is reconstructible from commit `1713f77d1307c40e7c00c3955a00b3c3d4b25515`.
- Unverified items: None required for this L1 cleanup.
- Follow-up tasks: None.

## Rollback

- Code: Restore the twelve scripts from Git history or move them back from `legacy-backend-scripts/`.
- Artifacts: Move the required report/temp/brand/tooling item back according to the archive README.
- Data: None.
