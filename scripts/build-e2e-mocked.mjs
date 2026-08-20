import { existsSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

/**
 * Production build for the mocked Playwright E2E suite. `playwright.mocked
 * .config.ts` starts this output with `next start` -- a real production
 * server instead of `next dev` -- so hydration, route caching, and
 * environment-variable inlining match what actually ships. `verify.mjs`'s
 * `e2e-mocked` mode runs this exactly once before invoking Playwright, so a
 * flaky-test retry inside that same Playwright run reuses the already-built
 * output and the already-started server rather than rebuilding.
 *
 * A stale `.next-e2e-mocked/` left over from a previous, incompatible build
 * can leave generated typed-route files behind (observed: a stray
 * `validator.ts`) that fail a fresh `next build --webpack` with an unrelated
 * TypeScript error. The directory is gitignored and safe to delete, so this
 * script always starts from a clean one.
 */
const workspaceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const frontendRoot = resolve(workspaceRoot, "frontend");
const nextCli = resolve(frontendRoot, "node_modules/next/dist/bin/next");
const distDirName = ".next-e2e-mocked";
const distDir = resolve(frontendRoot, distDirName);

if (!existsSync(nextCli)) {
  console.error(`Missing ${nextCli}. Run npm ci in ${frontendRoot} first.`);
  process.exit(1);
}

if (existsSync(distDir)) {
  console.log(`[build-e2e-mocked] removing stale ${distDirName}/`);
  rmSync(distDir, { recursive: true, force: true });
}

console.log("[build-e2e-mocked] next build --webpack");
const result = spawnSync(process.execPath, [nextCli, "build", "--webpack"], {
  cwd: frontendRoot,
  env: { ...process.env, NEXT_DIST_DIR: distDirName },
  stdio: "inherit",
  shell: false,
});

if (result.error) {
  throw result.error;
}
process.exit(result.status ?? 1);
