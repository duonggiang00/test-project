import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * CANONICAL_PROJECT_SPEC.md §10.3 item 5 -- "Material upload and AI content
 * generation with review".
 *
 * Mocked tier: the review queue's real behavior lives in the backend's
 * PostgreSQL integration suite, which already asserts row counts at every
 * transition. What this flow can only prove in a browser is that the UI walks
 * the state machine correctly -- that publish is unreachable until an explicit
 * approval lands, and that nothing is written before it.
 */

const ADMIN = {
  id: 'mock-admin-id',
  email: 'admin@example.com',
  role: 'admin',
  full_name: 'Mock Admin',
};

const MATERIAL = {
  id: 'material-1',
  title: 'AI source material',
  file_type: 'txt',
  ai_status: 'completed',
};

type JobStatus =
  | 'awaiting_review'
  | 'approved'
  | 'rejected'
  | 'published';

const generationJob = (status: JobStatus, version: number) => ({
  id: 'job-1',
  owner_id: ADMIN.id,
  material_id: MATERIAL.id,
  use_case: 'question_generation',
  status,
  version,
  draft_payload: null,
  failure_code: null,
  reviewer_id: status === 'awaiting_review' ? null : ADMIN.id,
  created_at: '2026-08-19T00:00:00Z',
  reviewed_at: status === 'awaiting_review' ? null : '2026-08-19T01:00:00Z',
  published_at: status === 'published' ? '2026-08-19T02:00:00Z' : null,
});

const signInAsAdmin = async (page: Page) => {
  await page.route('**/api/proxy/auth/me', async route => {
    await route.fulfill({
      status: 200,
      json: { ...ADMIN, is_active: true },
    });
  });
  await page.route('**/api/auth/login', async route => {
    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mocked-e2e-token',
        domain: '127.0.0.1',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax',
      },
    ]);
    await route.fulfill({ status: 200, json: { user: ADMIN } });
  });

  await page.goto('/login');
  await page.getByTestId('login-email-input').fill(ADMIN.email);
  await page.getByTestId('login-password-input').fill('mock-password');
  await page.getByTestId('login-submit-button').click();
  await page.waitForURL('/dashboard');
  await page.getByRole('heading', { name: /Dashboard/i }).waitFor();
};

test('material upload and AI generation are publishable only after review (MOCKED)', {
  tag: '@owner-frontend',
}, async ({ page }, testInfo) => {
  // --- MOCK STATE ---
  let materials: Record<string, unknown>[] = [];
  let jobStatus: JobStatus = 'awaiting_review';
  let jobVersion = 4;
  let publishCalls = 0;
  let approveCalls = 0;
  const publishBodies: Record<string, unknown>[] = [];

  // The removed `/materials/{id}/save-*` routes are the bypass this feature
  // exists to close. Any request to one is a regression, so record every
  // request rather than trusting that no handler serves them.
  const requestedPaths: string[] = [];
  page.on('request', request => {
    const { pathname } = new URL(request.url());
    if (pathname.startsWith('/api/proxy')) requestedPaths.push(pathname);
  });

  await page.route('**/api/proxy/**', async route => {
    await route.fulfill({
      status: 501,
      json: {
        error_code: 'UNHANDLED_MOCK_ROUTE',
        path: new URL(route.request().url()).pathname,
      },
    });
  });

  await page.route('**/api/proxy/analytics**', async route => {
    const { pathname } = new URL(route.request().url());
    if (pathname.endsWith('/topic-performance')) {
      await route.fulfill({ status: 200, json: [] });
    } else {
      await route.fulfill({
        status: 200,
        json: {
          total_students: 0,
          total_exams: 0,
          total_questions: 0,
          total_submissions: 0,
        },
      });
    }
  });

  await page.route('**/api/proxy/topics**', async route => {
    await route.fulfill({
      status: 200,
      json: {
        items: [{ id: 'topic-1', name: 'Review Topic', description: null }],
        total: 1,
        page: 1,
        size: 100,
        pages: 1,
      },
    });
  });

  await page.route('**/api/proxy/materials**', async (route: Route) => {
    const request = route.request();
    const { pathname } = new URL(request.url());

    if (request.method() === 'POST' && pathname.endsWith('/upload')) {
      // Upload produces a material, never publishable content of its own.
      materials = [MATERIAL];
      await route.fulfill({ status: 201, json: MATERIAL });
      return;
    }

    if (request.method() === 'POST' && pathname.endsWith('/generate-questions')) {
      // Additive response: the original payload key plus the review job the
      // draft was parked in.
      await route.fulfill({
        status: 200,
        json: {
          job_id: 'job-1',
          status: 'awaiting_review',
          questions: [
            {
              type: 'SINGLE_CHOICE',
              content: 'Which statement about the source material is true?',
              points: 1,
              difficulty: 'MEDIUM',
              options: [
                { content: 'The reviewed answer', is_correct: true },
                { content: 'A distractor', is_correct: false },
              ],
            },
          ],
        },
      });
      return;
    }

    if (request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        json: {
          items: materials,
          total: materials.length,
          page: 1,
          size: 50,
          pages: 1,
        },
      });
      return;
    }

    await route.fulfill({ status: 501, json: { error_code: 'UNHANDLED_MOCK_ROUTE' } });
  });

  await page.route('**/api/proxy/ai/generation-jobs/**', async (route: Route) => {
    const request = route.request();
    const { pathname } = new URL(request.url());

    if (request.method() === 'GET') {
      await route.fulfill({ status: 200, json: generationJob(jobStatus, jobVersion) });
      return;
    }

    if (pathname.endsWith('/approve')) {
      approveCalls += 1;
      expect(JSON.parse(request.postData() || '{}')).toEqual({
        expected_version: jobVersion,
      });
      jobStatus = 'approved';
      jobVersion += 1;
      await route.fulfill({ status: 200, json: generationJob(jobStatus, jobVersion) });
      return;
    }

    if (pathname.endsWith('/publish')) {
      publishCalls += 1;
      publishBodies.push(JSON.parse(request.postData() || '{}'));
      jobStatus = 'published';
      jobVersion += 1;
      await route.fulfill({
        status: 200,
        json: { job_id: 'job-1', status: 'published', saved_count: 1, question_ids: ['q-1'] },
      });
      return;
    }

    await route.fulfill({ status: 501, json: { error_code: 'UNHANDLED_MOCK_ROUTE' } });
  });

  await signInAsAdmin(page);

  // Reach the workspace through the intended navigation flow. The admin
  // sidebar is `hidden md:flex` and the mobile header's menu button has no
  // handler, so on the mobile project there is no in-product path to follow.
  if (testInfo.project.name === 'mobile-chrome') {
    await page.goto('/ai-workspace');
  } else {
    await page.getByRole('link', { name: 'AI Workspace' }).click();
    await page.waitForURL('/ai-workspace');
  }

  // --- UPLOAD ---
  await page.getByRole('combobox').selectOption('topic-1');
  await page.locator('input[type="file"]').setInputFiles({
    name: 'source.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Source material body'),
  });
  await expect(page.getByText(MATERIAL.title)).toBeVisible();

  // Upload notifications are transient. Verify and dismiss them immediately
  // after upload instead of waiting through the slower generation flow.
  const uploadToast = page.getByText('Upload queued', { exact: true });
  await expect(uploadToast).toBeVisible();
  for (const toastName of ['Upload queued', 'Uploading...']) {
    const toastDialog = page.getByRole('dialog', { name: toastName });
    await toastDialog.getByLabel('Close toast').click();
    await expect(toastDialog).not.toBeVisible();
  }
  await expect(uploadToast).not.toBeVisible();
  await expect(page.locator('[data-slot="toast"]')).toHaveCount(0);

  // --- GENERATE ---
  await page.getByText(MATERIAL.title).click();
  await expect(page.getByPlaceholder('Enter a material question...')).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Send material question' })).toBeDisabled();
  await page.getByRole('button', { name: 'Generate Questions' }).click();

  // --- AWAITING REVIEW: approve/reject offered, publish withheld ---
  const reviewPanel = page.getByTestId('generation-job-review');
  await expect(reviewPanel).toBeVisible();
  await expect(page.getByTestId('generation-job-status')).toHaveAttribute(
    'data-status',
    'awaiting_review',
  );
  await expect(reviewPanel.getByRole('button', { name: 'Approve' })).toBeVisible();
  await expect(reviewPanel.getByRole('button', { name: 'Reject' })).toBeVisible();
  await expect(reviewPanel.getByRole('button', { name: 'Publish' })).toHaveCount(0);
  expect(publishCalls).toBe(0);

  const safetyWarning = page.getByText('[WARNING] AI output may be incorrect.');
  await expect(safetyWarning).toBeVisible();
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  });
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('ai-review-awaiting-review.png', {
    animations: 'disabled',
    fullPage: true,
  });

  // --- APPROVE ---
  await reviewPanel.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByTestId('generation-job-status')).toHaveAttribute(
    'data-status',
    'approved',
  );
  await expect(reviewPanel.getByRole('button', { name: 'Publish' })).toBeVisible();
  await expect(reviewPanel.getByRole('button', { name: 'Approve' })).toHaveCount(0);
  await expect(reviewPanel.getByRole('button', { name: 'Reject' })).toHaveCount(0);
  expect(approveCalls).toBe(1);
  expect(publishCalls).toBe(0);

  // --- PUBLISH ---
  await reviewPanel.getByRole('button', { name: 'Publish' }).click();
  await expect(page.getByTestId('generation-job-status')).toHaveAttribute(
    'data-status',
    'published',
  );
  await expect(reviewPanel.getByRole('button', { name: 'Publish' })).toHaveCount(0);
  expect(publishCalls).toBe(1);

  // Publish carries placement only; the content comes from the job's reviewed
  // draft server-side.
  expect(Object.keys(publishBodies[0]).sort()).toEqual([
    'expected_version',
    'title',
    'topic_id',
  ]);

  // No request ever reached a removed single-click save route.
  expect(requestedPaths.filter(path => path.includes('/save-'))).toEqual([]);
});
