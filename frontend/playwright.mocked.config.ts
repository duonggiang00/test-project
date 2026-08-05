import { defineConfig, devices } from '@playwright/test';

const baseURL = 'http://127.0.0.1:3000';
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /admin-flow\.spec\.ts/,
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
    command: 'npm run dev -- --hostname 127.0.0.1',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
  },
});
