import { fireEvent, render, screen } from "@testing-library/react";

import { ExamResultView } from "@/components/features/student/ExamResultView";
import { useStudentExamResult } from "@/hooks/useStudentExams";

const push = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../../src/hooks/useStudentExams", () => ({
  useStudentExamResult: jest.fn(),
}));

jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: () => <div data-testid="result-bar" />,
  CartesianGrid: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

jest.mock(
  "../../src/components/features/student/BrutalistMatchingUI",
  () => ({
    __esModule: true,
    default: ({
      pairs,
      currentMatches,
      readOnly,
    }: {
      pairs: Array<{ left: string; right: string }>;
      currentMatches: Array<{ left: string; right: string }>;
      readOnly: boolean;
    }) => (
      <div data-testid="matching-review">
        {readOnly ? "readonly" : "interactive"}:{pairs.length}:{JSON.stringify(currentMatches)}
      </div>
    ),
  }),
);

const mockedUseStudentExamResult = jest.mocked(useStudentExamResult);

describe("ExamResultView", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders loading and missing-result states with a working exit", () => {
    mockedUseStudentExamResult.mockReturnValue({
      result: undefined,
      isLoading: true,
      isError: undefined,
    });
    const view = render(<ExamResultView examId="exam-1" />);
    expect(screen.getByText("Loading results...")).toBeVisible();

    mockedUseStudentExamResult.mockReturnValue({
      result: undefined,
      isLoading: false,
      isError: new Error("missing"),
    });
    view.rerender(<ExamResultView examId="exam-1" />);
    expect(screen.getByText("Exam result not found")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Back to home" }));
    expect(push).toHaveBeenCalledWith("/student/home");
  });

  test("renders every supported answer format without leaking answer parsing details", () => {
    mockedUseStudentExamResult.mockReturnValue({
      result: {
        exam_id: "exam-1",
        title: "Comprehensive Exam",
        total_score: 7,
        max_score: 10,
        correct_count: 3,
        incorrect_count: 5,
        time_taken_seconds: 125,
        answers: [
          {
            question_id: "single",
            content: "Pick one",
            question_type: "single_choice",
            options: [
              { id: "a", content: "Alpha", is_correct: true },
              { id: "b", content: "Beta", is_correct: false },
            ],
            answer_data: { selected_option_ids: ["a"] },
            is_correct: true,
            points_awarded: 1,
            points: 1,
          },
          {
            question_id: "multiple",
            content: "Pick several",
            question_type: "multiple_choice",
            options: [{ id: "b", content: "Beta", is_correct: true }],
            answer_data: { selected_option_id: "b" },
            is_correct: false,
            points_awarded: 0,
            points: 2,
          },
          {
            question_id: "boolean",
            content: "True or false",
            question_type: "true_false",
            options: [{ id: "true", content: "True", is_correct: true }],
            answer_data: { selected_option: "true" },
            is_correct: true,
            points_awarded: 1,
            points: 1,
          },
          {
            question_id: "blank",
            content: "A [BLANK] statement",
            question_type: "fill_in_blank",
            metadata_json: {
              blanks: [{ blank_index: 0, acceptable_answers: ["covered"] }],
            },
            options: [],
            answer_data: JSON.stringify({ blanks: { 0: "covered" } }),
            is_correct: true,
            points_awarded: 2,
            points: 2,
          },
          {
            question_id: "short",
            content: "Explain [BLANK] and [BLANK]",
            question_type: "short_answer",
            options: [],
            answer_data: { blanks: { 0: "first" } },
            is_correct: false,
            points_awarded: 1,
            points: 2,
          },
          {
            question_id: "matching-object",
            content: "Match object data",
            question_type: "matching",
            metadata_json: { pairs: [{ left: "One", right: "1" }] },
            options: [],
            answer_data: { matches: { One: "1" } },
            is_correct: true,
            points_awarded: 1,
            points: 1,
          },
          {
            question_id: "matching-array",
            content: "Match array data",
            question_type: "matching",
            metadata_json: { pairs: [{ left: "Two", right: "2" }] },
            options: [],
            answer_data: { matches: [{ left: "Two", right: "wrong" }] },
            is_correct: false,
            points_awarded: 0,
            points: 1,
          },
          {
            question_id: "unknown",
            content: "Unsupported format",
            question_type: "essay",
            options: [],
            answer_data: null,
            is_correct: false,
            points_awarded: 0,
            points: 1,
          },
        ],
      } as never,
      isLoading: false,
      isError: undefined,
    });

    render(<ExamResultView examId="exam-1" />);

    expect(screen.getByRole("heading", { name: "RESULT: Comprehensive Exam" })).toBeVisible();
    expect(screen.getByTestId("total-score")).toHaveTextContent("7 / 10");
    expect(screen.getByText("2m 05s")).toBeVisible();
    expect(screen.getAllByText("Your answer")).toHaveLength(3);
    expect(screen.getAllByText("covered")).toHaveLength(2);
    expect(screen.getAllByText("Not answered").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("matching-review")).toHaveLength(2);
    expect(screen.getByText(/readonly:1.*One.*1/)).toBeVisible();
    expect(screen.getByText(/readonly:1.*Two.*wrong/)).toBeVisible();
    expect(screen.getByText("Unknown question format.")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Exam list" }));
    expect(push).toHaveBeenCalledWith("/student/home");
  });

  test("treats malformed serialized answer data as unanswered", () => {
    mockedUseStudentExamResult.mockReturnValue({
      result: {
        exam_id: "exam-2",
        title: "Malformed Answers",
        total_score: 0,
        max_score: 1,
        correct_count: 0,
        incorrect_count: 1,
        time_taken_seconds: 0,
        answers: [{
          question_id: "bad-json",
          content: "Bad source payload",
          question_type: "single_choice",
          options: [{ id: "a", content: "Alpha", is_correct: true }],
          answer_data: "{not-json",
          is_correct: false,
          points_awarded: 0,
          points: 1,
        }],
      } as never,
      isLoading: false,
      isError: undefined,
    });

    render(<ExamResultView examId="exam-2" />);
    expect(screen.queryByText("Your answer")).not.toBeInTheDocument();
    expect(screen.getByText("Correct answer")).toBeVisible();
  });
});
