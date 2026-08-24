# Change Contract: REPORT-001 - Complete the PlayStudy project report

Risk level: L0
Owner: Codex primary agent
Approval required: No
Approval evidence: User requested implementation of the approved report plan.

## Scope
- In scope: Rewrite the Vietnamese Markdown report from committed `HEAD` evidence, add report diagrams/assets, and publish visually verified DOCX/PDF artifacts.
- Out of scope: Application code, API contracts, database migrations, deployment, and feature implementation.

## Behavior
- Before: The report contains sample metadata, broad implementation claims, incomplete evidence, and data/design descriptions that are not consistently tied to a commit.
- After: The report emphasizes working user flows and the educational problems they solve, with concise technical evidence tied to commit `1713f77`.
- Preserved invariants: Existing cover metadata remains unchanged; uncommitted application changes are excluded from claims.

## Expected files and contracts
- Files/modules: `Khung báo cáo dự án mẫu.md`, `docs/report-assets/`, `output/docx/`, `output/pdf/`, and a report builder under `scripts/`.
- API/event/schema impact: None.
- Migration/data impact: None.
- Security/ownership/tenant impact: None; the report distinguishes committed behavior from approved target policy.

## Verification contract
- Targeted tests: Summarize only minimal committed-snapshot evidence in the report.
- Static/type checks: Markdown links/assets and document structure.
- Integration/PostgreSQL checks: Not required for this documentation change; no production-readiness claim will be made.
- Build/E2E/visual checks: Committed frontend build evidence plus full-page DOCX/PDF render inspection.
- Manual verification: Compare Markdown, DOCX, and PDF content; inspect every rendered page.

## Rollback
- Code rollback: Remove the generated report files and restore the original Markdown.
- Data rollback: Not applicable.

## Archive note

The local Markdown source, report assets, generated DOCX/PDF/QA output, builder script, and committed-source snapshot were retired from the active workspace on 2026-08-20. They remain recoverable under `.legacy-archive/non-runtime-artifacts-20260820/report-generation/`; the original evidence snapshot can also be recreated from commit `1713f77d1307c40e7c00c3955a00b3c3d4b25515`.

## Assumptions and drift
- Verified assumptions: Frontend package files match `HEAD`; report screenshots depict the unchanged committed frontend; committed metadata exposes 14 SQLAlchemy tables.
- Unresolved assumptions: No verified production deployment or live PostgreSQL integration run is available for this report.
- SPEC_DRIFT: Committed authorization behavior and AI lifecycle do not yet fully demonstrate every approved target-policy requirement; the report will avoid presenting target policy as completed behavior.
