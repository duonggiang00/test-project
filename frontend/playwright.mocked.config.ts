import { resolve } from 'node:path';

import { defineConfig, devices } from '@playwright/test';

const host = '127.0.0.1';
const port = process.env.MOCKED_E2E_PORT ?? '3100';
const baseURL = `http://${host}:${port}`;
const nextCli = resolve(process.cwd(), 'node_modules/next/dist/bin/next');
const nextDistDir = '.next-e2e-mocked';

/**
 * This suite runs against a real production server, not `next dev`, so
 * hydration, route caching, and environment-variable inlining match what
 * actually ships. `node scripts/verify.mjs e2e-mocked` runs
 * `scripts/build-e2e-mocked.mjs` (a `next build --webpack` with
 * `NEXT_DIST_DIR=.next-e2e-mocked`, after clearing any stale build output)
 * exactly once before invoking Playwright; this config only starts the
 * already-built output with `next start`. Running this file directly (e.g.
 * `npx playwright test --config=playwright.mocked.config.ts`) requires that
 * build to already exist.
 */
const webServerCommand = `${JSON.stringify(process.execPath)} ${JSON.stringify(nextCli)} start --hostname ${host} --port ${port}`;

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /(?:admin-flow|ai-review-flow|grade-submission-flow)\.spec\.ts/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 60_000,
  reporter: [
    ['line'],
    ['html', { outputFolder: 'reports/playwright/mocked-html', open: 'never' }],
    ['json', { outputFile: 'reports/playwright/mocked.json' }],
  ],
  outputDir: 'reports/playwright/mocked-results',
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    testIdAttribute: 'data-testid',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: webServerCommand,
    env: { NEXT_DIST_DIR: nextDistDir },
    url: baseURL,
    reuseExistingServer: false,
    // A production start is typically fast, but budget generously above the
    // Playwright default (60s) since this can share the machine with the
    // build step that just ran and with other suites.
    timeout: 120_000,
    // Defaults are stdout: 'ignore', stderr: 'pipe' -- meaning the server's
    // own stdout is silently discarded unless overridden. A failed `next
    // start` (e.g. the build is missing or the port is unexpectedly taken)
    // must leave its own console output somewhere debuggable, not just a
    // generic Playwright timeout.
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
