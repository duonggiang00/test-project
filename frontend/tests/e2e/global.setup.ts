import { test as setup, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const authDir = path.join(process.cwd(), 'playwright/.auth');
if (!fs.existsSync(authDir)) {
  fs.mkdirSync(authDir, { recursive: true });
}

setup('authenticate as admin', { tag: '@owner-frontend' }, async ({ page }) => {
  await page.goto('/login');
  
  // Wait for network/hydration
  await page.waitForLoadState('networkidle');

  // Login as admin
  await page.getByTestId('login-email-input').fill('admin@example.com');
  await page.getByTestId('login-password-input').fill('12345678');
  await page.getByTestId('login-submit-button').click();

  // Wait for the URL to change to the admin dashboard
  await page.waitForURL('/dashboard');
  await expect(page).toHaveURL('/dashboard');

  // Save storage state
  await page.context().storageState({ path: path.join(authDir, 'admin.json') });
});

setup('authenticate as student', { tag: '@owner-frontend' }, async ({ page }) => {
  await page.goto('/login');
  
  // Wait for network/hydration
  await page.waitForLoadState('networkidle');

  // Login as student
  await page.getByTestId('login-email-input').fill('student@example.com');
  await page.getByTestId('login-password-input').fill('12345678');
  await page.getByTestId('login-submit-button').click();

  // Wait for the URL to change to the student home
  await page.waitForURL('/student/home');
  await expect(page).toHaveURL('/student/home');

  // Save storage state
  await page.context().storageState({ path: path.join(authDir, 'student.json') });
});
