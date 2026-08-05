import { Page, expect } from '@playwright/test';

export class ExamBuilderPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async addQuestion(content: string, type: 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'FILL_IN_BLANK' | 'MATCHING', points: number, options?: {content: string, isCorrect: boolean}[]) {
    await this.page.getByTestId('add-question-button').click();
    await this.page.getByTestId('question-content-input').fill(content);
    await this.page.getByTestId('question-type-select').selectOption({ value: type });
    await this.page.getByTestId('question-points-input').fill(points.toString());

    if (options && (type === 'SINGLE_CHOICE' || type === 'MULTIPLE_CHOICE')) {
      for (let i = 0; i < options.length; i++) {
        const optionInputs = this.page.getByTestId('option-content-input');
        const count = await optionInputs.count();
        if (i >= count) {
          await this.page.getByTestId('add-option-button').click();
        }
        await optionInputs.nth(i).fill(options[i].content);
        if (options[i].isCorrect) {
          await this.page.getByTestId('option-correct-checkbox').nth(i).check();
        } else {
           const checkbox = this.page.getByTestId('option-correct-checkbox').nth(i);
           const typeAttr = await checkbox.getAttribute('type');
           if (typeAttr === 'checkbox') {
             await checkbox.uncheck();
           }
        }
      }
    }

    await this.page.getByTestId('save-question-button').click();
    await expect(this.page.getByTestId('save-question-button')).toBeHidden();
  }

  async deleteQuestion(contentSubstring: string) {
    const questionCard = this.page.locator('div.border-4.border-black.p-6.bg-white', { hasText: contentSubstring }).first();
    this.page.once('dialog', dialog => dialog.accept());
    await questionCard.getByTestId('delete-question-button').click();
  }
}
