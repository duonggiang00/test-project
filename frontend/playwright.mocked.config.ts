import { resolve } from 'node:path';

import { defineConfig, devices } from '@playwright/test';

const host = '127.0.0.1';
const port = process.env.MOCKED_E2E_PORT ?? '3100';
const baseURL = `http://${host}:${port}`;
const nextCli = resolve(process.cwd(), 'node_modules/next/dist/bin/next');
const webServerCommand = `${JSON.stringify(process.execPath)} ${JSON.stringify(nextCli)} dev --hostname ${host} --port ${port}`;

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /(?:admin-flow|ai-review-flow)\.spec\.ts/,
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
    env: { NEXT_DIST_DIR: '.next-e2e-mocked' },
    url: baseURL,
    reuseExistingServer: false,
  },
});
