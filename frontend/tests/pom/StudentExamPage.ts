import { Page, expect } from '@playwright/test';

export class StudentExamPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Navigate to the student home page.
   */
  async gotoHome() {
    await this.page.goto('/student/home');
  }

  /**
   * Select an exam from the featured list on the home page by its title.
   * Assumes data-testid on the start button is `start-exam-{title}`
   */
  async selectExamByTitle(title: string) {
    const startButton = this.page.getByTestId(`start-exam-${title}`);
    await startButton.click();
  }

  /**
   * Answers a SINGLE_CHOICE or MULTIPLE_CHOICE question.
   * 
   * @param questionId The ID of the question (e.g., from the API or a known test value)
   * @param optionIds A list of option IDs to select. For SINGLE_CHOICE, pass a single element.
   */
  async answerMultipleChoiceQuestion(questionId: string, optionIds: string[]) {
    for (const optionId of optionIds) {
      const optionInput = this.page.getByTestId(`option-${questionId}-${optionId}`);
      // Using .check() handles both radio buttons and checkboxes
      await optionInput.check();
    }
  }

  /**
   * Answers a FILL_IN_BLANK question.
   * 
   * @param questionId The ID of the question
   * @param blankIndex The zero-based index of the blank
   * @param answer The string to fill into the blank
   */
  async answerFillInBlankQuestion(questionId: string, blankIndex: number, answer: string) {
    const blankInput = this.page.getByTestId(`blank-${questionId}-${blankIndex}`);
    await blankInput.fill(answer);
  }

  /**
   * Answers a MATCHING question.
   * 
   * @param questionId The ID of the question
   * @param leftSide The left string to match from
   * @param rightSide The right string to select from the dropdown
   */
  async answerMatchingQuestion(questionId: string, leftSide: string, rightSide: string) {
    const matchSelect = this.page.getByTestId(`match-${questionId}-${leftSide}`);
    await matchSelect.selectOption(rightSide);
  }

  /**
   * Submits the exam by clicking the submit button and confirming any dialogues.
   */
  async submitExam() {
    // If the browser shows a confirmation dialog, we need to accept it automatically
    this.page.once('dialog', dialog => dialog.accept());
    
    const submitBtn = this.page.getByTestId('submit-exam-button');
    await submitBtn.click();
    
    // Optionally wait for navigation to the result page
    await this.page.waitForURL(/\/student\/exam\/.*\/result/);
  }

  /**
   * Retrieves the final score from the result page.
   * Returns a string like "10 / 100"
   */
  async getFinalScore(): Promise<string> {
    const scoreElement = this.page.getByTestId('total-score');
    await expect(scoreElement).toBeVisible();
    return await scoreElement.innerText();
  }
}
