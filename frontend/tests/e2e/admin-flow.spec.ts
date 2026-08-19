import { expect, test, type Page } from '@playwright/test';
import { AdminDashboardPage } from '../pom/AdminDashboardPage';
import { ExamBuilderPage } from '../pom/ExamBuilderPage';

const assertSquareMonochromeAuthSurface = async (page: Page) => {
  const surface = page.getByTestId('auth-shell');
  await expect(surface).toBeVisible();

  const roundedElements = await surface.locator('*').evaluateAll(elements =>
    elements
      .filter(element => getComputedStyle(element).borderRadius !== '0px')
      .map(element => ({
        tag: element.tagName,
        radius: getComputedStyle(element).borderRadius,
      })),
  );
  expect(roundedElements).toEqual([]);

  const nonMonochromePaint = await surface.locator('*').evaluateAll(elements => {
    const allowed = new Set([
      'rgb(0, 0, 0)',
      'rgb(255, 255, 255)',
      'rgba(0, 0, 0, 0)',
    ]);
    const findings: Array<{ tag: string; property: string; value: string }> = [];

    for (const element of elements) {
      const style = getComputedStyle(element);
      for (const [property, value] of [
        ['color', style.color],
        ['backgroundColor', style.backgroundColor],
      ] as const) {
        if (!allowed.has(value)) {
          findings.push({ tag: element.tagName, property, value });
        }
      }

      const borderProperties = [
        ['borderTopWidth', 'borderTopColor'],
        ['borderRightWidth', 'borderRightColor'],
        ['borderBottomWidth', 'borderBottomColor'],
        ['borderLeftWidth', 'borderLeftColor'],
      ] as const;
      for (const [widthProperty, colorProperty] of borderProperties) {
        const width = style[widthProperty];
        const color = style[colorProperty];
        if (width !== '0px' && !allowed.has(color)) {
          findings.push({
            tag: element.tagName,
            property: colorProperty,
            value: color,
          });
        }
      }
    }

    return findings;
  });
  expect(nonMonochromePaint).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
};

test('PlayStudy branding is consistent on public and student surfaces', {
  tag: '@owner-frontend',
}, async ({ browser, page }) => {
  await page.goto('/');
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });

  await expect(page).toHaveTitle('PlayStudy');
  await expect(page.getByRole('link', { name: 'PlayStudy home' })).toBeVisible();
  await expect(page.getByTestId('playstudy-mark')).toHaveCSS('border-radius', '0px');
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute('href', /favicon\.ico/);
  await expect(page.locator('header').first()).toHaveScreenshot('landing-header.png', {
    animations: 'disabled',
    caret: 'hide',
  });

  const origin = new URL(page.url()).origin;
  const studentContext = await browser.newContext();
  await studentContext.addCookies([
    {
      name: 'token',
      value: 'mocked-student-token',
      url: origin,
      httpOnly: true,
      sameSite: 'Lax',
    },
    {
      name: 'role',
      value: 'student',
      url: origin,
      sameSite: 'Lax',
    },
  ]);
  await studentContext.addInitScript(() => {
    localStorage.setItem('user-storage', JSON.stringify({
      state: {
        user: {
          id: 'mock-student-id',
          email: 'student@example.test',
          role: 'student',
          full_name: 'Mock Student',
        },
      },
      version: 0,
    }));
  });
  const studentPage = await studentContext.newPage();
  await studentPage.route('**/api/proxy/auth/me', route => route.fulfill({
    status: 200,
    json: {
      id: 'mock-student-id',
      email: 'student@example.test',
      role: 'student',
      full_name: 'Mock Student',
    },
  }));
  await studentPage.route('**/api/proxy/topics**', route => route.fulfill({
    status: 200,
    json: { items: [], total: 0, page: 1, size: 50, pages: 0 },
  }));

  await studentPage.goto(`${origin}/student/home`);
  const studentBrand = studentPage.getByRole('link', { name: 'PlayStudy student home' });
  await expect(studentBrand).toBeVisible();
  await expect(studentPage.getByTestId('playstudy-mark')).toHaveCSS('border-radius', '0px');
  await expect(studentBrand).toHaveScreenshot('student-header-brand.png', {
    animations: 'disabled',
    caret: 'hide',
  });
  await studentContext.close();
});

test('auth surfaces are square, monochrome, responsive, and visually stable', {
  tag: '@owner-frontend',
}, async ({ page }, testInfo) => {
  await page.addInitScript(() => localStorage.removeItem('user-storage'));
  await page.goto('/login');
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await assertSquareMonochromeAuthSurface(page);
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  await expect(page).toHaveScreenshot('login-page.png', {
    animations: 'disabled',
    caret: 'hide',
    fullPage: true,
  });

  await page.goto('/register');
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await assertSquareMonochromeAuthSurface(page);
  await expect(page.getByRole('heading', { name: 'Register' })).toBeVisible();
  await expect(page.getByText('Self-service registration creates a student account.')).toBeVisible();
  await expect(page).toHaveScreenshot('register-page.png', {
    animations: 'disabled',
    caret: 'hide',
    fullPage: true,
  });

  if (testInfo.project.name === 'mobile-chrome') {
    await page.setViewportSize({ width: 360, height: 800 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    ).toBe(true);
    await page.evaluate(() => {
      document.documentElement.style.fontSize = '200%';
    });
    await expect(page.getByRole('button', { name: 'Create student account' })).toBeVisible();
    const overflowingElements = await page.locator('[data-auth-surface], [data-auth-surface] *').evaluateAll(
      elements => elements
        .map(element => {
          const bounds = element.getBoundingClientRect();
          return {
            tag: element.tagName,
            text: element.textContent?.trim().slice(0, 80),
            left: Math.round(bounds.left),
            right: Math.round(bounds.right),
          };
        })
        .filter(({ left, right }) => left < 0 || right > document.documentElement.clientWidth),
    );
    expect(overflowingElements).toEqual([]);
  }
});

test('login follows a predictable keyboard order with visible focus', {
  tag: '@owner-frontend',
}, async ({ page }, testInfo) => {
  await page.goto('/login');
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await expect(page.getByTestId('auth-shell')).toBeVisible();

  const focusOrder = [
    page.getByRole('link', { name: 'Home' }),
    page.getByLabel('Email'),
    page.getByLabel('Password', { exact: true }),
    page.getByRole('button', { name: 'Show password' }),
    page.getByRole('checkbox', { name: 'Remember me' }),
    page.getByRole('link', { name: 'Forgot password?' }),
    page.getByRole('button', { name: 'Sign in' }),
    page.getByRole('link', { name: 'Register' }),
  ];

  const keyboardOrder = testInfo.project.name === 'webkit'
    ? [focusOrder[1], focusOrder[2], focusOrder[3], focusOrder[4], focusOrder[6]]
    : focusOrder;

  await keyboardOrder[0].focus();
  await expect(keyboardOrder[0]).toBeFocused();

  for (const control of keyboardOrder.slice(1)) {
    await page.keyboard.press('Tab');
    await expect(control).toBeFocused();
  }

  for (const link of [focusOrder[0], focusOrder[5], focusOrder[7]]) {
    await link.focus();
    await expect(link).toBeFocused();
    expect(await link.evaluate(element => getComputedStyle(element).outlineStyle)).toBe('solid');
  }
});

test('student registration returns to login with a one-time success notice', {
  tag: '@owner-frontend',
}, async ({ page }) => {
  await page.route('**/api/proxy/auth/register', async route => {
    await route.fulfill({
      status: 201,
      json: {
        id: 'mock-student-id',
        email: 'student@example.test',
        role: 'student',
        full_name: 'Mock Student',
      },
    });
  });

  await page.goto('/register');
  await page.getByLabel('Full name').fill('Mock Student');
  await page.getByLabel('Email').fill('student@example.test');
  await page.getByLabel('Password', { exact: true }).fill('mock-password');
  await page.getByLabel('Confirm password', { exact: true }).fill('mock-password');
  await page.getByRole('button', { name: 'Create student account' }).click();

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('status')).toContainText('Account created');
});

test('admin flow: create and delete topic, exam, and question (MOCKED)', {
  tag: '@owner-frontend',
}, async ({ page }) => {
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
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname.endsWith('/topic-performance')) {
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
    await route.fulfill({
      status: 200,
      json: {
        user: {
          id: 'mock-admin-id',
          email: 'admin@example.com',
          role: 'admin',
          full_name: 'Mock Admin',
        },
      },
    });
  });

  await page.goto('/login');
  await page.getByTestId('login-email-input').fill('admin@example.com');
  await page.getByTestId('login-password-input').fill('mock-password');
  await page.getByTestId('login-submit-button').click();
  await page.waitForURL('/dashboard');
  await page.getByRole('heading', { name: /Dashboard/i }).waitFor();

  // --- MOCK STATE ---
  let mockTopics: Record<string, unknown>[] = [{ id: "t1", name: "Existing Topic", description: "Old" }];
  let mockExams: Record<string, unknown>[] = [];
  let mockQuestions: Record<string, unknown>[] = [];

  // --- API INTERCEPTION ---
  await page.route('**/api/proxy/topics**', async route => {
    const method = route.request().method();
    if (method === 'POST') {
      const data = JSON.parse(route.request().postData() || '{}');
      const newTopic = { id: "mock-topic-id", name: data.name, description: data.description };
      mockTopics = [newTopic, ...mockTopics];
      await route.fulfill({ status: 201, json: newTopic });
    } else if (method === 'DELETE') {
      mockTopics = mockTopics.filter(t => t.name !== 'E2E Topic');
      await route.fulfill({ status: 200, json: { message: "Deleted" } });
    } else if (method === 'GET') {
      await route.fulfill({ status: 200, json: { items: mockTopics, total: mockTopics.length, page: 1, size: 50, pages: 1 } });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/proxy/exams**', async route => {
    const method = route.request().method();
    const requestUrl = new URL(route.request().url());
    if (method === 'POST' && requestUrl.pathname.endsWith('/questions')) {
      const data = JSON.parse(route.request().postData() || '{}');
      const newQuestion = {
        id: 'mock-question-id',
        content: data.content,
        points: data.points,
        question_type: data.question_type,
        difficulty: data.difficulty,
        is_ai_generated: false,
        options: data.options.map((option: Record<string, unknown>, index: number) => ({
          id: `mock-option-${index}`,
          ...option,
        })),
      };
      mockQuestions = [newQuestion, ...mockQuestions];
      await route.fulfill({ status: 201, json: newQuestion });
    } else if (method === 'POST') {
      const data = JSON.parse(route.request().postData() || '{}');
      const newExam = { id: "mock-exam-id", title: data.title, description: data.description, topic_id: data.topic_id, duration_minutes: data.duration_minutes };
      mockExams = [newExam, ...mockExams];
      await route.fulfill({ status: 201, json: newExam });
    } else if (method === 'DELETE') {
      mockExams = mockExams.filter(e => e.title !== 'E2E Exam');
      await route.fulfill({ status: 200, json: { message: "Deleted" } });
    } else if (method === 'GET' && requestUrl.pathname.endsWith('/mock-exam-id')) {
      await route.fulfill({
        status: 200,
        json: { ...mockExams[0], questions: mockQuestions },
      });
    } else if (method === 'GET') {
      await route.fulfill({ status: 200, json: { items: mockExams, total: mockExams.length, page: 1, size: 50, pages: 1 } });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/proxy/questions**', async route => {
    const method = route.request().method();
    if (method === 'POST') {
      const data = JSON.parse(route.request().postData() || '{}');
      const newQuestion = { id: "mock-question-id", content: data.content, options: data.options };
      mockQuestions = [newQuestion, ...mockQuestions];
      await route.fulfill({ status: 201, json: newQuestion });
    } else if (method === 'DELETE') {
      mockQuestions = mockQuestions.filter(q => q.content !== 'What is Playwright?');
      await route.fulfill({ status: 200, json: { message: "Deleted" } });
    } else if (method === 'GET') {
      await route.fulfill({ status: 200, json: { items: mockQuestions, total: mockQuestions.length, page: 1, size: 50, pages: 1 } });
    } else {
      await route.continue();
    }
  });

  const adminPage = new AdminDashboardPage(page);
  const builderPage = new ExamBuilderPage(page);

  // Initialize AdminDashboardPage and go to /topics
  await adminPage.gotoTopics();
  await expect(page.getByTestId('add-topic-button')).toBeVisible();
  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await expect(page).toHaveScreenshot('topics-page.png', {
    animations: 'disabled',
    caret: 'hide',
    fullPage: true,
  });

  // Create a topic 'E2E Topic'
  await adminPage.createTopic('E2E Topic', 'E2E Topic Description', 'keyboard');

  // Go to /exams and create an exam 'E2E Exam'
  await adminPage.gotoExams();
  await adminPage.createExam('E2E Exam', 'E2E Exam Description', 60, 'E2E Topic');

  // Open the exam builder for 'E2E Exam'
  await adminPage.openExamBuilder('E2E Exam');

  // Use ExamBuilderPage to add 1 multiple choice question
  await builderPage.addQuestion('What is Playwright?', 'SINGLE_CHOICE', 10, [
    { content: 'A testing framework', isCorrect: true },
    { content: 'A playwright', isCorrect: false }
  ]);

  // Delete the question
  await builderPage.deleteQuestion('What is Playwright?');

  // Go back and delete the 'E2E Exam'
  await adminPage.gotoExams();
  await adminPage.deleteExam('E2E Exam');

  // Go back and delete the 'E2E Topic'
  await adminPage.gotoTopics();
  await adminPage.deleteTopic('E2E Topic');
});
