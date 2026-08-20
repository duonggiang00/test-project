import { existsSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { platform } from "node:os";

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
const mockedE2EPort = process.env.MOCKED_E2E_PORT ?? "3100";

if (!existsSync(nextCli)) {
  console.error(`Missing ${nextCli}. Run npm ci in ${frontendRoot} first.`);
  process.exit(1);
}

/**
 * `next start` (Playwright's `webServer.command`) can outlive the
 * Playwright process that started it: on Windows, a timed-out or crashed
 * run doesn't reliably kill the whole process tree (`next start` forks a
 * separate server process; killing the CLI wrapper doesn't kill it), so a
 * stale listener can be left holding the port. `webServer.reuseExistingServer:
 * false` then makes the *next* run hard-fail immediately with "port already
 * used" -- a message that has nothing to do with whatever actually failed
 * last time, and that failure mode was observed directly during review.
 *
 * Freeing the port before every build makes a bad prior run self-healing
 * (the next invocation just works) instead of a manual "go kill the
 * process" step. This is intentionally best-effort: if the platform tool
 * isn't available or nothing is listening, it silently no-ops rather than
 * failing the build over a cleanup step.
 */
function freeStalePort(port) {
  try {
    if (platform() === "win32") {
      const netstat = spawnSync("netstat", ["-ano"], { encoding: "utf8" });
      const lines = (netstat.stdout ?? "").split(/\r?\n/);
      const pids = new Set();
      for (const line of lines) {
        if (!line.includes(`:${port} `) && !line.endsWith(`:${port}`)) continue;
        if (!/LISTENING/.test(line)) continue;
        const columns = line.trim().split(/\s+/);
        const pid = columns[columns.length - 1];
        if (/^\d+$/.test(pid)) pids.add(pid);
      }
      for (const pid of pids) {
        console.log(
          `[build-e2e-mocked] freeing stale listener on port ${port} (pid ${pid})`,
        );
        spawnSync("taskkill", ["/F", "/PID", pid, "/T"], { stdio: "ignore" });
      }
    } else {
      const lsof = spawnSync("lsof", ["-ti", `tcp:${port}`], { encoding: "utf8" });
      for (const pid of (lsof.stdout ?? "").split(/\r?\n/).filter(Boolean)) {
        console.log(
          `[build-e2e-mocked] freeing stale listener on port ${port} (pid ${pid})`,
        );
        spawnSync("kill", ["-9", pid], { stdio: "ignore" });
      }
    }
  } catch {
    // Best-effort: a missing platform tool must not fail the build.
  }
}

freeStalePort(mockedE2EPort);

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
