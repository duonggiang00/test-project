import { test, expect } from '@playwright/test';
import { StudentExamPage } from '../pom/StudentExamPage';
import { AdminDashboardPage } from '../pom/AdminDashboardPage';
import { ExamBuilderPage } from '../pom/ExamBuilderPage';

test('Student can take an exam and view the result', {
  tag: '@owner-frontend',
}, async ({ browser }) => {
  // 1. Create an admin context to create a fresh exam
  const adminContext = await browser.newContext({ storageState: 'playwright/.auth/admin.json' });
  const adminPage = await adminContext.newPage();
  const adminDashboard = new AdminDashboardPage(adminPage);
  const examBuilder = new ExamBuilderPage(adminPage);

  const examTitle = `Student E2E Exam ${Date.now()}`;
  const topicTitle = `Student E2E Topic ${Date.now()}`;

  await adminDashboard.gotoTopics();
  await adminDashboard.createTopic(topicTitle, 'E2E Testing Topic');
  await adminDashboard.gotoExams();
  await adminDashboard.createExam(examTitle, 'E2E Testing Exam', 60, topicTitle);
  await adminDashboard.openExamBuilder(examTitle);
  await examBuilder.addQuestion('What is 2+2?', 'SINGLE_CHOICE', 10, [
    { content: '4', isCorrect: true },
    { content: '5', isCorrect: false }
  ]);
  await adminContext.close();

  // 2. Create a student context to take the exam
  const studentContext = await browser.newContext({ storageState: 'playwright/.auth/student.json' });
  const page = await studentContext.newPage();
  const studentPage = new StudentExamPage(page);

  // Initialize StudentExamPage and go to /student/home
  await studentPage.gotoHome();
  await studentPage.selectTopicByTitle(topicTitle);

  // Start the newly created exam
  await studentPage.selectExamByTitle(examTitle);

  // Inside the exam, use POM methods to answer the first question
  const firstOption = page.locator('[data-testid^="option-"]').first();
  await expect(firstOption).toBeVisible({ timeout: 10000 });

  const optionTestId = await firstOption.getAttribute('data-testid');
  if (optionTestId) {
    // Format is option-{questionId}-{optionId}
    const parts = optionTestId.split('-');
    if (parts.length >= 3) {
      const questionId = parts[1];
      const optionId = parts.slice(2).join('-');
      
      // Use the POM method to answer the question
      await studentPage.answerMultipleChoiceQuestion(questionId, [optionId]);
    } else {
      await firstOption.check(); // Fallback
    }
  } else {
    await firstOption.check(); // Fallback
  }

  // Click submit exam
  await studentPage.submitExam();

  // Verify the final score element is visible on the result page
  const score = await studentPage.getFinalScore();
  expect(score).toBeDefined();

  // Submitted educational records are retained. Prove the destructive guard
  // instead of treating a closed confirmation modal as successful cleanup.
  // The guarded E2E runner drops the entire isolated database after the suite.
  const adminCleanupContext = await browser.newContext({ storageState: 'playwright/.auth/admin.json' });
  const cleanupPage = await adminCleanupContext.newPage();
  const cleanupDashboard = new AdminDashboardPage(cleanupPage);
  await cleanupDashboard.gotoExams();
  const blockedDelete = cleanupPage.waitForResponse(
    response => response.request().method() === 'DELETE'
      && response.url().includes('/api/proxy/exams/'),
  );
  await cleanupDashboard.deleteExam(examTitle);
  const deleteResponse = await blockedDelete;
  expect(deleteResponse.status()).toBe(409);
  expect(await deleteResponse.json()).toMatchObject({
    error_code: 'EXAM_DELETE_BLOCKED_BY_RETAINED_RECORDS',
  });
  await cleanupDashboard.expectExamVisible(examTitle);
  await adminCleanupContext.close();
  
  await studentContext.close();
});
