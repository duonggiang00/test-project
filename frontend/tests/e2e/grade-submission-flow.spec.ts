import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * CANONICAL_PROJECT_SPEC.md §10.3 item 4 -- "Teacher views and grades the
 * result".
 *
 * Mocked tier: the correction's real behavior -- ownership scoping, the
 * `[0, question.points]` bound, total recomputation, the audit event -- lives
 * in the backend's PostgreSQL integration suite. What only a browser can prove
 * is that the flow exists end to end: that a teacher can reach a submission
 * from the dashboard, change one answer's score, and that the request leaving
 * the page carries exactly the two fields the contract defines. `is_correct`
 * and `total_score` are derived and recomputed server-side, so a body carrying
 * either would be a client asserting a total it has no right to assert.
 */

const ADMIN = {
  id: 'mock-admin-id',
  email: 'admin@example.com',
  role: 'admin',
  full_name: 'Mock Admin',
};

const SUBMISSION_ID = '11111111-1111-4111-8111-111111111111';
const QUESTION_ID = '22222222-2222-4222-8222-222222222222';

/** The question is worth 5; the automatic grader awarded 0 by exact match. */
const MAX_POINTS = 5;

const submissionDetail = (
  pointsAwarded: number,
  override: { reason: string; at: string } | null,
) => ({
  id: SUBMISSION_ID,
  exam_id: '33333333-3333-4333-8333-333333333333',
  student_id: '44444444-4444-4444-8444-444444444444',
  student_name: 'Nguyen Van A',
  student_email: 'student@example.com',
  exam_title: 'Kiem tra giua ky',
  status: 'submitted',
  // Recomputed server-side as the sum of the answers.
  total_score: pointsAwarded,
  start_time: '2026-08-19T00:00:00Z',
  answers: [
    {
      question_id: QUESTION_ID,
      question_content: 'Thu do cua Viet Nam la gi?',
      answer_data: { text: 'Thu do Ha Noi' },
      is_correct: pointsAwarded === MAX_POINTS,
      points_awarded: pointsAwarded,
      max_points: MAX_POINTS,
      override_reason: override?.reason ?? null,
      overridden_at: override?.at ?? null,
    },
  ],
});

const submissionListItem = (totalScore: number) => ({
  id: SUBMISSION_ID,
  student_name: 'Nguyen Van A',
  exam_title: 'Kiem tra giua ky',
  total_score: totalScore,
  max_score: MAX_POINTS,
  status: 'submitted',
  submitted_at: '2026-08-19T00:30:00Z',
});

const signInAsAdmin = async (page: Page) => {
  await page.route('**/api/auth/login', async route => {
    await page.context().addCookies([
      {
        name: 'token',
        value: 'mocked-e2e-token',
        domain: '127.0.0.1',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax',
      },
      {
        name: 'role',
        value: 'admin',
        domain: '127.0.0.1',
        path: '/',
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

test('a teacher views a submission and corrects one answer score (MOCKED)', {
  tag: '@owner-frontend',
}, async ({ page }, testInfo) => {
  // --- MOCK STATE ---
  let storedPoints = 0;
  let storedOverride: { reason: string; at: string } | null = null;
  const gradeRequests: { method: string; body: Record<string, unknown> }[] = [];

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
          total_students: 1,
          total_exams: 1,
          total_questions: 1,
          total_submissions: 1,
        },
      });
    }
  });

  await page.route('**/api/proxy/history/**', async (route: Route) => {
    const request = route.request();
    const { pathname } = new URL(request.url());

    if (request.method() === 'PUT' && pathname.endsWith('/grade')) {
      gradeRequests.push({
        method: request.method(),
        body: JSON.parse(request.postData() || '{}'),
      });
      expect(pathname).toBe(
        `/api/proxy/history/submissions/${SUBMISSION_ID}` +
          `/answers/${QUESTION_ID}/grade`,
      );
      storedPoints = MAX_POINTS;
      storedOverride = {
        reason: 'Hoc sinh dien dat khac nhung dung y',
        at: '2026-08-19T10:00:00Z',
      };
      await route.fulfill({
        status: 200,
        json: submissionDetail(storedPoints, storedOverride),
      });
      return;
    }

    if (request.method() === 'GET' && pathname.endsWith(SUBMISSION_ID)) {
      await route.fulfill({
        status: 200,
        json: submissionDetail(storedPoints, storedOverride),
      });
      return;
    }

    if (request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        json: {
          items: [submissionListItem(storedPoints)],
          total: 1,
          page: 1,
          size: 10,
          pages: 1,
        },
      });
      return;
    }

    await route.fulfill({
      status: 501,
      json: { error_code: 'UNHANDLED_MOCK_ROUTE' },
    });
  });

  await signInAsAdmin(page);

  // Reach the submission through the intended navigation flow. The admin
  // sidebar is `hidden md:flex` and the mobile header's menu button has no
  // handler, so on the mobile project there is no in-product path to follow.
  if (testInfo.project.name === 'mobile-chrome') {
    await page.goto('/history');
  } else {
    await page.getByRole('link', { name: 'History' }).click();
    await page.waitForURL('/history');
  }

  // --- VIEW THE RESULT ---
  await expect(page.getByText('Nguyen Van A')).toBeVisible();
  await page.getByRole('button', { name: 'View Details' }).click();
  await page.waitForURL(`/history/${SUBMISSION_ID}`);
  await expect(page.getByText('0 POINTS')).toBeVisible();

  const editor = page.getByTestId(`answer-grade-editor-${QUESTION_ID}`);
  await expect(editor).toBeVisible();
  // Nobody has corrected this answer yet, so there is no trail to show.
  await expect(
    page.getByTestId(`answer-grade-trail-${QUESTION_ID}`),
  ).toHaveCount(0);

  const pointsField = editor.getByLabel(/New Score/);
  const reasonField = editor.getByLabel(/Correction Reason/);
  const saveButton = editor.getByRole('button', { name: /Save Score/ });

  // --- THE SCORE IS BOUNDED BY THE QUESTION'S OWN MAXIMUM ---
  await expect(pointsField).toHaveAttribute('max', String(MAX_POINTS));

  // --- A REASON IS REQUIRED BEFORE ANYTHING CAN BE SENT ---
  await expect(saveButton).toBeDisabled();
  await pointsField.fill(String(MAX_POINTS));
  await expect(saveButton).toBeDisabled();

  // --- AN OUT-OF-RANGE SCORE IS NEVER SENT ---
  await reasonField.fill('Hoc sinh dien dat khac nhung dung y');
  await pointsField.fill(String(MAX_POINTS + 1));
  await expect(saveButton).toBeDisabled();
  expect(gradeRequests).toHaveLength(0);

  // --- CORRECT THE SCORE ---
  await pointsField.fill(String(MAX_POINTS));
  await expect(saveButton).toBeEnabled();
  await saveButton.click();

  // --- THE RECOMPUTED TOTAL AND THE TRAIL COME BACK FROM THE SERVER ---
  await expect(
    page.getByTestId(`answer-grade-trail-${QUESTION_ID}`),
  ).toContainText('CORRECTED');
  await expect(page.getByText(`${MAX_POINTS} POINTS`)).toBeVisible();

  // --- CONTRACT: the body carries exactly `points_awarded` and `reason` ---
  expect(gradeRequests).toHaveLength(1);
  expect(gradeRequests[0].method).toBe('PUT');
  expect(Object.keys(gradeRequests[0].body).sort()).toEqual([
    'points_awarded',
    'reason',
  ]);
  expect(gradeRequests[0].body).toEqual({
    points_awarded: MAX_POINTS,
    reason: 'Hoc sinh dien dat khac nhung dung y',
  });
});
