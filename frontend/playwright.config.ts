import { resolve } from 'node:path';

import { defineConfig, devices } from '@playwright/test';

const host = '127.0.0.1';
const port = process.env.REAL_E2E_PORT ?? '3101';
const baseURL = `http://${host}:${port}`;
const nextCli = resolve(process.cwd(), 'node_modules/next/dist/bin/next');
const webServerCommand = `${JSON.stringify(process.execPath)} ${JSON.stringify(nextCli)} dev --hostname ${host} --port ${port}`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 60_000,
  reporter: [
    ['line'],
    ['html', { outputFolder: 'reports/playwright/real-html', open: 'never' }],
    ['json', { outputFile: 'reports/playwright/real.json' }],
  ],
  outputDir: 'reports/playwright/real-results',
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    testIdAttribute: 'data-testid',
  },
  testMatch: /student-flow\.spec\.ts/,
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    }
  ],
  webServer: {
    command: webServerCommand,
    env: { NEXT_DIST_DIR: '.next-e2e-real' },
    url: baseURL,
    reuseExistingServer: false,
  },
});
