import { Page, expect } from '@playwright/test';

export class AdminDashboardPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async gotoTopics() {
    await this.page.goto('/topics');
  }

  async gotoExams() {
    await this.page.goto('/exams');
    await expect(this.page).toHaveURL(/\/exams$/);
  }

  async createTopic(
    name: string,
    description: string,
    activation: 'pointer' | 'keyboard' = 'pointer',
  ) {
    const addButton = this.page.getByTestId('add-topic-button');
    if (activation === 'keyboard') {
      await addButton.focus();
      await expect(addButton).toBeFocused();
      await this.page.keyboard.press('Enter');
    } else {
      await addButton.click();
    }
    await this.page.getByTestId('topic-name-input').fill(name);
    await this.page.getByTestId('topic-description-input').fill(description);
    await this.page.getByTestId('save-topic-button').click();
    await expect(this.page.getByTestId('save-topic-button')).toBeHidden();
  }

  async deleteTopic(topicName: string) {
    await this.page.getByTestId('search-topic-input').fill(topicName);
    const row = this.page.locator('tr').filter({ hasText: topicName }).first();
    this.page.once('dialog', dialog => dialog.accept());
    await row.getByTestId('delete-topic-button').click();
  }

  async createExam(title: string, description: string, duration: number, topicName?: string) {
    await this.page.getByTestId('add-exam-button').click();
    await this.page.getByTestId('exam-title-input').fill(title);
    await this.page.getByTestId('exam-description-input').fill(description);
    if (topicName) {
      await this.page.getByTestId('exam-topic-select').selectOption({ label: topicName });
    }
    await this.page.getByTestId('exam-duration-input').fill(duration.toString());
    
    await expect(this.page.getByTestId('exam-published-checkbox')).toBeHidden();
    await this.page.getByTestId('save-exam-button').click();
    await this.page.waitForURL(/\/exams\/[^/?]+$/);
  }

  async createDraftFromOpenForm(
    title: string,
    description: string,
    duration: number,
    topicName: string,
  ) {
    await expect(this.page.getByRole('heading', { name: 'Create Exam Draft' })).toBeVisible();
    await expect(this.page.getByTestId('exam-published-checkbox')).toBeHidden();
    await this.page.getByTestId('exam-title-input').fill(title);
    await this.page.getByTestId('exam-description-input').fill(description);
    await this.page.getByTestId('exam-topic-select').selectOption({ label: topicName });
    await this.page.getByTestId('exam-duration-input').fill(duration.toString());
    await this.page.getByTestId('save-exam-button').click();
    await this.page.waitForURL(/\/exams\/[^/?]+$/);
  }

  async deleteExam(examTitle: string) {
    await this.page.getByTestId('search-exam-input').fill(examTitle);
    const row = this.page.getByTestId(`exam-row-${examTitle}`).first();
    await row.getByTestId('delete-exam-button').click();
    await this.page.getByTestId('confirm-delete-exam-button').click();
    await expect(this.page.getByTestId('confirm-delete-exam-button')).toBeHidden();
  }

  async expectExamVisible(examTitle: string) {
    await this.page.getByTestId('search-exam-input').fill(examTitle);
    await expect(
      this.page.getByTestId(`exam-row-${examTitle}`).first(),
    ).toBeVisible();
  }

  async openExamBuilder(examTitle: string) {
    await this.page.getByTestId('search-exam-input').fill(examTitle);
    const row = this.page.getByTestId(`exam-row-${examTitle}`).first();
    await row.getByTestId('exam-builder-link').click();
  }

  async publishExam(examTitle: string) {
    await this.page.getByTestId('search-exam-input').fill(examTitle);
    const row = this.page.getByTestId(`exam-row-${examTitle}`).first();
    await row.getByTestId('edit-exam-button').click();
    await this.page.getByTestId('exam-published-checkbox').check();
    await this.page.getByTestId('save-exam-button').click();
    await expect(this.page.getByTestId('save-exam-button')).toBeHidden();
  }
}
