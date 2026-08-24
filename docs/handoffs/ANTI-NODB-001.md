# Handoff: ANTI-NODB-001 No-database anti-pattern remediation

Status: DONE
Risk level: L2

## Outcome

- Requirements/task IDs: `ANTI-NODB-001`, `GUARD-008`.
- Replaced the remote Material Symbols font with a shared Lucide adapter and removed all 71 icon-font usages.
- Bundled IBM Plex Mono locally at weights 400, 500, 600, and 700 with source, license, and SHA-256 provenance.
- Reworked the global design tokens and legacy effect styles to use only opaque black and white, square radii, and hard-edged shadows.
- Reduced the architecture baseline from 338 findings to 10: all 328 executable design findings are resolved; the remaining 10 are database-query findings deliberately deferred by this contract.
- Removed the orphan browser script and improved architecture-guard precision and CSS coverage in the preceding guard checkpoint.

## Files changed

- `frontend/src/app/layout.tsx`, `frontend/src/app/globals.css`, and `frontend/src/assets/fonts/ibm-plex-mono/` — local font and monochrome foundation.
- `frontend/src/components/ui/app-icon.tsx` plus affected feature components — typed shared Lucide rendering in place of icon-font text.
- Affected frontend routes/components — black-and-white token normalization and reviewed interaction-state contrast.
- `frontend/tests/e2e/admin-flow.spec.ts-snapshots/` — reviewed IBM Plex Mono desktop/mobile visual baselines.
- `config/architecture-guard-baseline.json` — generated current baseline containing only deferred database findings.

## Verification

| Command | Exit | Collected | Passed | Failed | Relevant result |
|---|---:|---:|---:|---:|---|
| `node scripts/verify.mjs fast` | 0 | Backend 336; frontend 132 | 468 | 0 | `VERIFY_OK mode=fast`; generated contracts, Ruff, mypy, ESLint, Jest, and production build passed. |
| `node scripts/architecture-guard.mjs check` | 0 | 10 current findings | 10 baseline matches | 0 additions | `ARCHITECTURE_OK current=10 baseline=10`; design findings are zero. |
| `node scripts/architecture-guard.mjs fixtures` | 0 | 23 bad-fixture findings | 21 rules | 0 | `good=0 bad=23 rules=21`. |
| `npm run lint` | 0 | Frontend source | All | 0 | ESLint passed. |
| `npm run test:unit -- --runInBand` | 0 | 27 suites / 132 tests | 132 | 0 | Jest passed with no snapshots. |
| `npm run build` | 0 | 28 application routes | All | 0 | Next.js production compilation, TypeScript, static generation, and trace collection passed. |
| `node scripts/verify.mjs e2e-mocked` | 0 | 28 | 28 | 0 | Production build plus Chromium, Firefox, WebKit, and Pixel 7 Chrome flows passed; owner/flake policy passed all 28 results. |

## Impact

- API/event/schema: none.
- Migration/data: none; no database connection or migration was used.
- Authentication/authorization/ownership: unchanged.
- Dependency/toolchain: no new package; `lucide-react` was already locked. Font binaries are repository-owned assets under the IBM Plex Open Font License.

## Manual evidence

- Inspected the rendered login, topics management, and mobile exam-draft screenshots at original resolution.
- Confirmed square controls, opaque monochrome styling, visible content hierarchy, desktop/mobile layout stability, and the intended IBM Plex Mono metrics before accepting new baselines.

## Risks and follow-up

- Browser installation initially hit a transient `ENOSPC` while unpacking WebKit. Playwright removed its temporary download, the isolated retry succeeded, and the canonical four-project suite then passed; no external cache was deleted.
- Ten backend query findings remain in `demo_data/loader.py` and `auth_service.py`. They require the separately approved PostgreSQL-capable track and are not represented as fixed here.
- A survey found 456 pre-existing non-ASCII source lines. A dedicated product-copy review should translate legacy UI strings without mixing that behavior/content change into this design remediation.

## Rollback

- Revert the `ANTI-NODB-001` implementation commit to restore the previous font, icons, CSS tokens, guard baseline, and visual snapshots.
- Data rollback is not applicable.
