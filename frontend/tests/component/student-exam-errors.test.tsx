import { Suspense } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import StudentExamTakingPage from "@/app/student/exam/[id]/page";
import { toast } from "@/components/ui/toast";
import { submitExam, useTakeExam } from "@/hooks/useStudentExams";

const push = jest.fn();
const confirm = jest.fn<Promise<boolean>, [string]>();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../../src/hooks/useStudentExams", () => ({
  useTakeExam: jest.fn(),
  submitExam: jest.fn(),
}));

jest.mock("../../src/hooks/useConfirm", () => ({
  useConfirm: () => ({
    confirm,
    ConfirmDialog: () => null,
  }),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedUseTakeExam = jest.mocked(useTakeExam);
const mockedSubmitExam = jest.mocked(submitExam);
const mockedToast = jest.mocked(toast.add);

describe("student exam submission errors", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    confirm.mockResolvedValue(true);
    mockedUseTakeExam.mockReturnValue({
      exam: {
        id: "exam-1",
        title: "Contract exam",
        duration_minutes: 30,
        remaining_seconds: 300,
        questions: [
          {
            id: "question-1",
            content: "Choose one",
            points: 1,
            question_type: "SINGLE_CHOICE",
            options: [{ id: "option-1", content: "Answer" }],
          },
        ],
      } as never,
      isLoading: false,
      isError: undefined,
    });
  });

  test("localizes the code without rendering raw legacy detail", async () => {
    mockedSubmitExam.mockRejectedValue({
      response: {
        data: {
          error_code: "ALREADY_SUBMITTED",
          details: {},
          request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
          detail: "canary raw submission detail",
        },
        config: { data: "canary student answers" },
      },
    });

    const params = Promise.resolve({ id: "exam-1" });
    await act(async () => {
      render(
        <Suspense fallback={<div>Loading</div>}>
          <StudentExamTakingPage params={params} />
        </Suspense>,
      );
      await params;
    });

    fireEvent.click(await screen.findByTestId("submit-exam-button"));

    await waitFor(() => expect(mockedSubmitExam).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(mockedToast).toHaveBeenCalledWith({
        title: "Submission failed",
        description: "This exam has already been submitted.",
        type: "error",
      }),
    );
    expect(JSON.stringify(mockedToast.mock.calls)).not.toContain("canary");
  });

  test("uses backend remaining time and confirms before discarding answers", async () => {
    const params = Promise.resolve({ id: "exam-1" });
    await act(async () => {
      render(
        <Suspense fallback={<div>Loading</div>}>
          <StudentExamTakingPage params={params} />
        </Suspense>,
      );
      await params;
    });

    expect(screen.getByText("05:00")).toBeVisible();
    fireEvent.click(screen.getByTestId("option-question-1-option-1"));

    confirm.mockResolvedValueOnce(false);
    fireEvent.click(screen.getByRole("button", { name: /EXIT EXAM/i }));
    await waitFor(() => expect(confirm).toHaveBeenCalledTimes(1));
    expect(push).not.toHaveBeenCalled();

    confirm.mockResolvedValueOnce(true);
    fireEvent.click(screen.getByRole("button", { name: /EXIT EXAM/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/student/home"));
  });

  test("answers legacy blanks and safe matching options without answer-key metadata", async () => {
    mockedUseTakeExam.mockReturnValue({
      exam: {
        id: "exam-1",
        title: "Question type contract exam",
        duration_minutes: 30,
        remaining_seconds: 300,
        questions: [
          {
            id: "fill-legacy",
            content: "Legacy answer: ___.",
            points: 1,
            question_type: "FILL_IN_BLANK",
            metadata_json: { blank_count: 1 },
            options: [],
          },
          {
            id: "fill-canonical",
            content: "Canonical [BLANK] and [BLANK].",
            points: 2,
            question_type: "FILL_IN_BLANK",
            metadata_json: { blank_count: 2 },
            options: [],
          },
          {
            id: "matching-1",
            content: "Match each concept.",
            points: 2,
            question_type: "MATCHING",
            metadata_json: {
              left_options: ["One", "Two"],
              right_options: ["Second", "First"],
            },
            options: [],
          },
        ],
      } as never,
      isLoading: false,
      isError: undefined,
    });
    mockedSubmitExam.mockResolvedValue({} as never);

    const params = Promise.resolve({ id: "exam-1" });
    await act(async () => {
      render(
        <Suspense fallback={<div>Loading</div>}>
          <StudentExamTakingPage params={params} />
        </Suspense>,
      );
      await params;
    });

    fireEvent.change(screen.getByLabelText("Blank 1 for question 1"), {
      target: { value: "legacy value" },
    });
    fireEvent.change(screen.getByLabelText("Blank 1 for question 2"), {
      target: { value: "first value" },
    });
    fireEvent.change(screen.getByLabelText("Blank 2 for question 2"), {
      target: { value: "second value" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Left option: One" }));
    fireEvent.click(screen.getByRole("button", { name: "Right option: First" }));
    expect(screen.getByTestId("mobile-matching-summary")).toHaveTextContent(
      "One→First",
    );

    fireEvent.click(screen.getByTestId("submit-exam-button"));

    await waitFor(() => expect(mockedSubmitExam).toHaveBeenCalledTimes(1));
    expect(mockedSubmitExam).toHaveBeenCalledWith(
      "exam-1",
      expect.objectContaining({
        answers: expect.arrayContaining([
          expect.objectContaining({
            question_id: "fill-legacy",
            answer_data: { blanks: { 0: "legacy value" } },
          }),
          expect.objectContaining({
            question_id: "fill-canonical",
            answer_data: {
              blanks: { 0: "first value", 1: "second value" },
            },
          }),
          expect.objectContaining({
            question_id: "matching-1",
            answer_data: { matches: [{ left: "One", right: "First" }] },
          }),
        ]),
      }),
    );
  });

  test("does not auto-submit again while a manual submission is pending", async () => {
    jest.useFakeTimers();
    mockedUseTakeExam.mockReturnValue({
      exam: {
        id: "exam-1",
        title: "Last second exam",
        duration_minutes: 30,
        remaining_seconds: 1,
        questions: [],
      } as never,
      isLoading: false,
      isError: undefined,
    });
    let resolveSubmission: (() => void) | undefined;
    mockedSubmitExam.mockReturnValue(
      new Promise((resolve) => {
        resolveSubmission = () => resolve({} as never);
      }),
    );

    try {
      const params = Promise.resolve({ id: "exam-1" });
      let rerender: ReturnType<typeof render>["rerender"] | undefined;
      await act(async () => {
        const view = render(
          <Suspense fallback={<div>Loading</div>}>
            <StudentExamTakingPage params={params} />
          </Suspense>,
        );
        rerender = view.rerender;
        await params;
      });

      fireEvent.click(screen.getByTestId("submit-exam-button"));
      await act(async () => {
        await Promise.resolve();
      });
      expect(mockedSubmitExam).toHaveBeenCalledTimes(1);

      mockedUseTakeExam.mockReturnValue({
        exam: {
          id: "exam-1",
          title: "Last second exam",
          duration_minutes: 30,
          remaining_seconds: 0,
          questions: [],
        } as never,
        isLoading: false,
        isError: undefined,
      });
      await act(async () => {
        rerender?.(
          <Suspense fallback={<div>Loading</div>}>
            <StudentExamTakingPage params={params} />
          </Suspense>,
        );
      });

      await act(async () => {
        jest.advanceTimersByTime(1_000);
      });
      expect(mockedSubmitExam).toHaveBeenCalledTimes(1);

      await act(async () => {
        resolveSubmission?.();
        await Promise.resolve();
      });
    } finally {
      jest.useRealTimers();
    }
  });
});
