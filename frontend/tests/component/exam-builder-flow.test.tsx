import React, { act, Suspense, type ReactNode } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ExamDetailPage from "@/app/(admin)/exams/[id]/page";
import QuestionsPage from "@/app/(admin)/questions/page";
import { createExamQuestion, useExamDetail } from "@/hooks/useExams";
import {
  createQuestion,
  useQuestions,
} from "@/hooks/useQuestions";
import { useTopics } from "@/hooks/useTopics";
import { bulkAddQuestionsToExam } from "@/services/apiService";
import {
  toCanonicalDifficulty,
  toCanonicalQuestionType,
} from "@/lib/questionEnums";
import type { ExamDetail, Question } from "@/types";

const mutateExam = jest.fn();
const mutateQuestionBank = jest.fn();
let currentSearchParams = new URLSearchParams();

jest.mock("next/navigation", () => ({
  notFound: () => null,
  useSearchParams: () => currentSearchParams,
}));

jest.mock("../../src/hooks/useExams", () => ({
  useExamDetail: jest.fn(),
  createExamQuestion: jest.fn(),
}));

jest.mock("../../src/hooks/useQuestions", () => ({
  useQuestions: jest.fn(),
  createQuestion: jest.fn(),
  updateQuestion: jest.fn(),
  deleteQuestion: jest.fn(),
}));

jest.mock("../../src/hooks/useTopics", () => ({
  useTopics: jest.fn(),
}));

jest.mock("../../src/services/apiService", () => ({
  bulkAddQuestionsToExam: jest.fn(),
}));

jest.mock("../../src/hooks/useConfirm", () => ({
  useConfirm: () => ({
    confirm: jest.fn(),
    ConfirmDialog: () => null,
  }),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

jest.mock("../../src/components/ui/tabs", () => ({
  Tabs: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children }: { children: ReactNode }) => (
    <button type="button">{children}</button>
  ),
  TabsContent: ({ children }: { children: ReactNode }) => <section>{children}</section>,
}));

const mockedUseExamDetail = jest.mocked(useExamDetail);
const mockedUseQuestions = jest.mocked(useQuestions);
const mockedUseTopics = jest.mocked(useTopics);
const mockedBulkAdd = jest.mocked(bulkAddQuestionsToExam);
const mockedCreateExamQuestion = jest.mocked(createExamQuestion);
const mockedCreateQuestion = jest.mocked(createQuestion);

const existingQuestion: Question = {
  id: "question-existing",
  content: "Already assigned",
  points: 1,
  question_type: "SINGLE_CHOICE",
  difficulty: "MEDIUM",
  options: [
    { id: "option-existing-a", content: "A", is_correct: true },
    { id: "option-existing-b", content: "B", is_correct: false },
  ],
};

const bankQuestion: Question = {
  id: "question-bank",
  content: "Available bank question",
  points: 2,
  question_type: "MULTIPLE_CHOICE",
  difficulty: "HARD",
  topic_id: "topic-1",
  options: [
    { id: "option-bank-a", content: "A", is_correct: true },
    { id: "option-bank-b", content: "B", is_correct: false },
  ],
};

const exam: ExamDetail = {
  id: "exam-1",
  title: "Python Quiz",
  description: "",
  duration_minutes: 45,
  is_published: false,
  topic_id: "topic-1",
  questions: [existingQuestion],
};

function mockQuestionList(questions: Question[] = [existingQuestion, bankQuestion]) {
  mockedUseQuestions.mockReturnValue({
    questions,
    pagination: {
      items: questions,
      total: questions.length,
      page: 1,
      size: 10,
      pages: 1,
    },
    data: undefined,
    isLoading: false,
    isError: undefined,
    mutate: mutateQuestionBank,
  });
}

async function renderExamBuilder(): Promise<void> {
  await act(async () => {
    render(
      <Suspense fallback={null}>
        <ExamDetailPage params={Promise.resolve({ id: "exam-1" })} />
      </Suspense>,
    );
  });
}

describe("exam question authoring and assignment", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    currentSearchParams = new URLSearchParams();
    mockedUseExamDetail.mockReturnValue({
      exam,
      isLoading: false,
      isError: undefined,
      mutate: mutateExam,
    });
    mockedUseTopics.mockReturnValue({
      topics: [{ id: "topic-1", name: "Python Basics", description: "" }],
      pagination: {} as never,
      data: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockQuestionList();
  });

  test("defaults the bank to the exam Topic and hides questions already assigned", async () => {
    await renderExamBuilder();

    expect(screen.getByLabelText(/Filter by topic/i)).toHaveValue("topic-1");
    expect(screen.queryByTestId("question-bank-item-question-existing"))
      .not.toBeInTheDocument();
    expect(screen.getByTestId("question-bank-item-question-bank")).toBeVisible();
  });

  test("bulk assigns selected questions and refreshes both server-state views", async () => {
    mockedBulkAdd.mockResolvedValue({ message: "Added 1 question" });
    await renderExamBuilder();

    fireEvent.click(screen.getByRole("checkbox", {
      name: /Select question: Available bank question/i,
    }));
    fireEvent.click(screen.getByRole("button", { name: /Add to Exam \(1\)/i }));

    await waitFor(() => expect(mockedBulkAdd).toHaveBeenCalledWith(
      "exam-1",
      ["question-bank"],
    ));
    expect(mutateExam).toHaveBeenCalledTimes(1);
    expect(mutateQuestionBank).toHaveBeenCalledTimes(1);
  });

  test("creates an exam question with canonical uppercase enums", async () => {
    mockedCreateExamQuestion.mockResolvedValue(bankQuestion);
    await renderExamBuilder();

    fireEvent.click(screen.getByTestId("add-question-button"));
    fireEvent.change(screen.getByTestId("question-content-input"), {
      target: { value: "Canonical enum question" },
    });
    fireEvent.change(screen.getByTestId("exam-question-difficulty-select"), {
      target: { value: "HARD" },
    });
    const optionInputs = screen.getAllByTestId("option-content-input");
    fireEvent.change(optionInputs[0], { target: { value: "Correct" } });
    fireEvent.change(optionInputs[1], { target: { value: "Incorrect" } });
    fireEvent.click(screen.getByTestId("save-question-button"));

    await waitFor(() => expect(mockedCreateExamQuestion).toHaveBeenCalledTimes(1));
    expect(mockedCreateExamQuestion).toHaveBeenCalledWith(
      "exam-1",
      expect.objectContaining({
        question_type: "SINGLE_CHOICE",
        difficulty: "HARD",
      }),
    );
  });

  test("the standalone Question Bank also emits canonical difficulty values", async () => {
    mockQuestionList([]);
    mockedCreateQuestion.mockResolvedValue(bankQuestion);
    render(<QuestionsPage />);

    fireEvent.click(screen.getByTestId("global-add-question-button"));
    fireEvent.change(screen.getByTestId("global-question-content-input"), {
      target: { value: "Question bank canonical enum" },
    });
    fireEvent.change(screen.getByTestId("global-question-difficulty-select"), {
      target: { value: "EASY" },
    });
    const optionInputs = screen.getAllByTestId("global-option-content-input");
    fireEvent.change(optionInputs[0], { target: { value: "Correct" } });
    fireEvent.change(optionInputs[1], { target: { value: "Incorrect" } });
    fireEvent.click(screen.getByTestId("global-save-question-button"));

    await waitFor(() => expect(mockedCreateQuestion).toHaveBeenCalledTimes(1));
    expect(mockedCreateQuestion).toHaveBeenCalledWith(expect.objectContaining({
      question_type: "SINGLE_CHOICE",
      difficulty: "EASY",
    }));
  });

  test("normalizes legacy response enums before a form can submit them", () => {
    expect(toCanonicalQuestionType("multiple_choice")).toBe("MULTIPLE_CHOICE");
    expect(toCanonicalQuestionType("single_choice")).toBe("SINGLE_CHOICE");
    expect(toCanonicalQuestionType("true_false")).toBe("SINGLE_CHOICE");
    expect(toCanonicalQuestionType("short_answer")).toBe("FILL_IN_BLANK");
    expect(toCanonicalDifficulty("easy")).toBe("EASY");
    expect(toCanonicalDifficulty("medium")).toBe("MEDIUM");
    expect(toCanonicalDifficulty("hard")).toBe("HARD");
  });
});
