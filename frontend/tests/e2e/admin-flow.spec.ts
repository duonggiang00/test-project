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
      name: 'access_token',
      value: 'mocked-student-token',
      url: origin,
      httpOnly: true,
      sameSite: 'Lax',
    },
  ]);
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

  // Windows WebKit follows the host convention that omits links from Tab
  // navigation. Linux WebKit includes links, matching the other CI browsers.
  const keyboardOrder = testInfo.project.name === 'webkit' && process.platform === 'win32'
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
}, async ({ page }, testInfo) => {
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

  await page.route('**/api/proxy/auth/me', async route => {
    await route.fulfill({
      status: 200,
      json: {
        id: 'mock-admin-id',
        email: 'admin@example.com',
        role: 'admin',
        full_name: 'Mock Admin',
        is_active: true,
      },
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
  const isMobile = testInfo.project.name === 'mobile-chrome';
  let mockTopics: Record<string, unknown>[] = [
    ...(isMobile ? [{ id: 'mock-topic-id', name: 'E2E Topic', description: 'E2E Topic Description' }] : []),
    { id: "t1", name: "Existing Topic", description: "Old" },
  ];
  let mockExams: Record<string, unknown>[] = [];
  let mockExamQuestions: Record<string, unknown>[] = [];
  const mockQuestionBank: Record<string, unknown>[] = [{
    id: 'bank-question-id',
    content: 'Which tool runs browser tests?',
    points: 5,
    question_type: 'SINGLE_CHOICE',
    difficulty: 'MEDIUM',
    topic_id: 'mock-topic-id',
    is_ai_generated: false,
    options: [
      { id: 'bank-option-1', content: 'Playwright', is_correct: true },
      { id: 'bank-option-2', content: 'Alembic', is_correct: false },
    ],
  }];
  let createdExamPayload: Record<string, unknown> | null = null;

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
      const requestUrl = new URL(route.request().url());
      if (requestUrl.pathname.endsWith('/mock-topic-id')) {
        await route.fulfill({
          status: 200,
          json: {
            id: 'mock-topic-id',
            name: 'E2E Topic',
            description: 'E2E Topic Description',
            parent_id: null,
            brief_content: null,
          },
        });
        return;
      }
      await route.fulfill({ status: 200, json: { items: mockTopics, total: mockTopics.length, page: 1, size: 50, pages: 1 } });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/proxy/exams**', async route => {
    const method = route.request().method();
    const requestUrl = new URL(route.request().url());
    if (method === 'POST' && requestUrl.pathname.endsWith('/questions/bulk')) {
      const data = JSON.parse(route.request().postData() || '{}');
      const selectedQuestions = mockQuestionBank.filter(question =>
        (data.question_ids as string[]).includes(question.id as string),
      );
      mockExamQuestions = [
        ...mockExamQuestions,
        ...selectedQuestions.filter(question =>
          !mockExamQuestions.some(existing => existing.id === question.id),
        ),
      ];
      await route.fulfill({ status: 200, json: { message: 'Questions assigned' } });
    } else if (method === 'POST' && requestUrl.pathname.endsWith('/questions')) {
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
      mockExamQuestions = [newQuestion, ...mockExamQuestions];
      await route.fulfill({ status: 201, json: newQuestion });
    } else if (method === 'POST') {
      const data = JSON.parse(route.request().postData() || '{}');
      createdExamPayload = data;
      const newExam = {
        id: "mock-exam-id",
        title: data.title,
        description: data.description,
        topic_id: data.topic_id,
        duration_minutes: data.duration_minutes,
        is_published: data.is_published,
      };
      mockExams = [newExam, ...mockExams];
      await route.fulfill({ status: 201, json: newExam });
    } else if (method === 'DELETE') {
      if (requestUrl.pathname.includes('/questions/')) {
        mockExamQuestions = mockExamQuestions.filter(question => question.id !== 'mock-question-id');
      } else {
        mockExams = mockExams.filter(e => e.title !== 'E2E Exam');
      }
      await route.fulfill({ status: 200, json: { message: "Deleted" } });
    } else if (method === 'GET' && requestUrl.pathname.endsWith('/mock-exam-id')) {
      await route.fulfill({
        status: 200,
        json: { ...mockExams[0], questions: mockExamQuestions },
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
      mockExamQuestions = [newQuestion, ...mockExamQuestions];
      await route.fulfill({ status: 201, json: newQuestion });
    } else if (method === 'DELETE') {
      mockExamQuestions = mockExamQuestions.filter(q => q.content !== 'What is Playwright?');
      await route.fulfill({ status: 200, json: { message: "Deleted" } });
    } else if (method === 'GET') {
      const allQuestions = [...mockExamQuestions, ...mockQuestionBank];
      await route.fulfill({ status: 200, json: { items: allQuestions, total: allQuestions.length, page: 1, size: 50, pages: 1 } });
    } else {
      await route.continue();
    }
  });

  const adminPage = new AdminDashboardPage(page);
  const builderPage = new ExamBuilderPage(page);

  await page.route('**/api/proxy/materials**', route => route.fulfill({
    status: 200,
    json: { items: [], total: 0, page: 1, size: 50, pages: 0 },
  }));
  await page.route('**/api/proxy/flashcards/topics/mock-topic-id/decks', route => route.fulfill({
    status: 200,
    json: [],
  }));

  // Start from dashboard navigation instead of entering /exams directly.
  if (isMobile) {
    await page.getByRole('link', { name: 'Open Exam Builder' }).click();
    await page.waitForURL('/exams');
    await page.getByTestId('add-exam-button').click();
  } else {
    await page.getByRole('link', { name: 'Topic Hub' }).click();
    await page.waitForURL('/topics');
    await expect(page.getByTestId('add-topic-button')).toBeVisible();
    await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
    await expect(page).toHaveScreenshot('topics-page.png', {
      animations: 'disabled',
      caret: 'hide',
      fullPage: true,
    });

    await adminPage.createTopic('E2E Topic', 'E2E Topic Description', 'keyboard');
    const topicRow = page.locator('tr', { hasText: 'E2E Topic' }).first();
    await topicRow.getByTestId('manage-topic-button').click();
    await page.waitForURL('/topics/mock-topic-id');
    await page.getByRole('tab', { name: 'Exams' }).click();
    await page.getByRole('button', { name: 'Create Exam' }).click();
    await expect(page).toHaveURL(/\/exams\?topic_id=mock-topic-id&create=1$/);
  }

  await page.addStyleTag({ content: 'nextjs-portal { display: none !important; }' });
  await expect(page).toHaveScreenshot('exam-create-draft.png', {
    animations: 'disabled',
    caret: 'hide',
    fullPage: true,
  });
  await adminPage.createDraftFromOpenForm('E2E Exam', 'E2E Exam Description', 60, 'E2E Topic');
  expect(createdExamPayload).toMatchObject({
    title: 'E2E Exam',
    topic_id: 'mock-topic-id',
    is_published: false,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await expect(page).toHaveScreenshot('exam-builder-empty.png', {
    animations: 'disabled',
    caret: 'hide',
    fullPage: true,
  });

  // Use ExamBuilderPage to add 1 multiple choice question
  await builderPage.addQuestion('What is Playwright?', 'SINGLE_CHOICE', 10, [
    { content: 'A testing framework', isCorrect: true },
    { content: 'A playwright', isCorrect: false }
  ]);

  // Assign an existing question from the Topic-scoped Question Bank.
  await page.getByRole('tab', { name: 'Ngân Hàng Câu Hỏi' }).click();
  const bankQuestion = page.getByTestId('question-bank-item-bank-question-id');
  await expect(bankQuestion).toContainText('Which tool runs browser tests?');
  await bankQuestion.getByRole('checkbox', { name: 'Select question: Which tool runs browser tests?' }).check();
  await page.getByRole('button', { name: 'Thêm vào Bài thi (1)' }).click();
  await page.getByRole('tab', { name: /Câu Hỏi Đề Thi/ }).click();
  await expect(page.getByText('What is Playwright?')).toBeVisible();
  await expect(page.getByText('Which tool runs browser tests?')).toBeVisible();

  // Delete the question
  await builderPage.deleteQuestion('What is Playwright?');

  // Go back and delete the 'E2E Exam'
  await adminPage.gotoExams();
  await adminPage.deleteExam('E2E Exam');

  if (!isMobile) {
    // The mobile path uses the existing Topic fixture and needs no Topic cleanup.
    await adminPage.gotoTopics();
    await adminPage.deleteTopic('E2E Topic');
  }
});
