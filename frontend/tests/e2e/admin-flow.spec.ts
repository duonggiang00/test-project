import { test } from '@playwright/test';
import { AdminDashboardPage } from '../pom/AdminDashboardPage';
import { ExamBuilderPage } from '../pom/ExamBuilderPage';

test.use({ storageState: 'playwright/.auth/admin.json' });

test('admin flow: create and delete topic, exam, and question (MOCKED)', async ({ page }) => {
  // --- MOCK STATE ---
  let mockTopics: Record<string, unknown>[] = [{ id: "t1", name: "Existing Topic", description: "Old" }];
  let mockExams: Record<string, unknown>[] = [];
  let mockQuestions: Record<string, unknown>[] = [];

  // --- API INTERCEPTION ---
  await page.route('**/api/proxy/topics*', async route => {
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

  await page.route('**/api/proxy/exams*', async route => {
    const method = route.request().method();
    if (method === 'POST') {
      const data = JSON.parse(route.request().postData() || '{}');
      const newExam = { id: "mock-exam-id", title: data.title, description: data.description, topic_id: data.topic_id, duration_minutes: data.duration_minutes };
      mockExams = [newExam, ...mockExams];
      await route.fulfill({ status: 201, json: newExam });
    } else if (method === 'DELETE') {
      mockExams = mockExams.filter(e => e.title !== 'E2E Exam');
      await route.fulfill({ status: 200, json: { message: "Deleted" } });
    } else if (method === 'GET') {
      await route.fulfill({ status: 200, json: { items: mockExams, total: mockExams.length, page: 1, size: 50, pages: 1 } });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/proxy/questions*', async route => {
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
  
  // Create a topic 'E2E Topic'
  await adminPage.createTopic('E2E Topic', 'E2E Topic Description');

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
