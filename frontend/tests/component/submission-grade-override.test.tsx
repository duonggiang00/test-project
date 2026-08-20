import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";

import HistoryDetailPage from "@/app/(admin)/history/[id]/page";
import { toast } from "@/components/ui/toast";
import { fetcher } from "@/hooks/useFetch";
import { updateSubmissionGrade } from "@/services/apiService";
import type { SubmissionAnswerDetail, SubmissionDetail } from "@/types";

jest.mock("../../src/hooks/useFetch", () => ({
  fetcher: jest.fn(),
}));

jest.mock("../../src/services/apiService", () => ({
  updateSubmissionGrade: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

jest.mock("next/navigation", () => ({
  notFound: () => null,
}));

const mockedFetcher = jest.mocked(fetcher);
const mockedUpdate = jest.mocked(updateSubmissionGrade);
const mockedToastAdd = jest.mocked(toast.add);

const SUBMISSION_ID = "11111111-1111-4111-8111-111111111111";
const QUESTION_ID = "22222222-2222-4222-8222-222222222222";

function answer(
  overrides: Partial<SubmissionAnswerDetail> = {},
): SubmissionAnswerDetail {
  return {
    question_id: QUESTION_ID,
    question_content: "Thủ đô của Việt Nam là gì?",
    answer_data: { text: "Ha Noi" },
    is_correct: false,
    points_awarded: 0,
    max_points: 5,
    override_reason: null,
    overridden_at: null,
    ...overrides,
  };
}

function submission(
  answers: SubmissionAnswerDetail[] = [answer()],
  overrides: Partial<SubmissionDetail> = {},
): SubmissionDetail {
  return {
    id: SUBMISSION_ID,
    exam_id: "33333333-3333-4333-8333-333333333333",
    student_id: "44444444-4444-4444-8444-444444444444",
    student_name: "Nguyen Van A",
    student_email: "student@example.com",
    exam_title: "Kiểm tra giữa kỳ",
    status: "submitted",
    total_score: 0,
    start_time: "2026-08-19T00:00:00Z",
    answers,
    ...overrides,
  } as SubmissionDetail;
}

/**
 * The page unwraps its route params with `use()`, so it suspends on first
 * render exactly as it does under the router. The boundary and the awaited
 * `act` are what let it resume; without them the tree never commits.
 */
async function renderPage(): Promise<void> {
  await act(async () => {
    render(
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
        <React.Suspense fallback={null}>
          <HistoryDetailPage params={Promise.resolve({ id: SUBMISSION_ID })} />
        </React.Suspense>
      </SWRConfig>,
    );
  });
}

const pointsInput = () =>
  screen.getByLabelText(/New Score/i) as HTMLInputElement;
const reasonInput = () =>
  screen.getByLabelText(/Correction Reason/i) as HTMLTextAreaElement;
const saveButton = () =>
  screen.getByRole("button", { name: /Save Score/i }) as HTMLButtonElement;

/** Wait for the submission to have loaded through SWR. */
const waitForEditor = () =>
  waitFor(() =>
    expect(
      screen.getByTestId(`answer-grade-editor-${QUESTION_ID}`),
    ).toBeInTheDocument(),
  );

describe("submission answer grade correction", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("bounds the score input by the question's max_points", async () => {
    mockedFetcher.mockResolvedValue(submission());
    await renderPage();
    await waitForEditor();

    expect(pointsInput()).toHaveAttribute("max", "5");
    expect(pointsInput()).toHaveAttribute("min", "0");
    // The legal range is stated in text, not implied by the control alone.
    expect(screen.getByText(/\(0 - 5\)/)).toBeInTheDocument();
  });

  test("refuses to send a score above max_points and says why", async () => {
    mockedFetcher.mockResolvedValue(submission());
    await renderPage();
    await waitForEditor();

    fireEvent.change(reasonInput(), { target: { value: "Chấm lại" } });
    fireEvent.change(pointsInput(), { target: { value: "6" } });

    expect(saveButton()).toBeDisabled();
    expect(screen.getByText(/Score must be between 0 and 5/)).
      toBeInTheDocument();
    expect(pointsInput()).toHaveAttribute("aria-invalid", "true");

    fireEvent.change(pointsInput(), { target: { value: "5" } });
    expect(saveButton()).toBeEnabled();
    expect(mockedUpdate).not.toHaveBeenCalled();
  });

  test("refuses a negative score", async () => {
    mockedFetcher.mockResolvedValue(submission());
    await renderPage();
    await waitForEditor();

    fireEvent.change(reasonInput(), { target: { value: "Chấm lại" } });
    fireEvent.change(pointsInput(), { target: { value: "-1" } });

    expect(saveButton()).toBeDisabled();
    expect(mockedUpdate).not.toHaveBeenCalled();
  });

  test("keeps save disabled while the reason is empty or blank", async () => {
    mockedFetcher.mockResolvedValue(submission());
    await renderPage();
    await waitForEditor();

    // A valid score alone is not enough; the backend requires a reason.
    fireEvent.change(pointsInput(), { target: { value: "4" } });
    expect(saveButton()).toBeDisabled();
    expect(
      screen.getByText(/A correction reason is required/),
    ).toBeInTheDocument();

    // Whitespace is blank to the server too, so it must not enable saving.
    fireEvent.change(reasonInput(), { target: { value: "   " } });
    expect(saveButton()).toBeDisabled();

    fireEvent.change(reasonInput(), { target: { value: "Đáp án đúng ý" } });
    expect(saveButton()).toBeEnabled();
  });

  test("sends exactly points_awarded and reason, then shows the new state", async () => {
    const corrected = submission(
      [
        answer({
          points_awarded: 5,
          is_correct: true,
          override_reason: "Đáp án đúng ý",
          overridden_at: "2026-08-19T10:00:00Z",
        }),
      ],
      { total_score: 5 },
    );
    mockedFetcher.mockResolvedValue(submission());
    mockedUpdate.mockResolvedValue(corrected);
    await renderPage();
    await waitForEditor();

    fireEvent.change(pointsInput(), { target: { value: "5" } });
    fireEvent.change(reasonInput(), { target: { value: "  Đáp án đúng ý  " } });
    fireEvent.click(saveButton());

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalledTimes(1));
    expect(mockedUpdate).toHaveBeenCalledWith(SUBMISSION_ID, QUESTION_ID, {
      points_awarded: 5,
      // The reason is trimmed; the server rejects a blank one anyway.
      reason: "Đáp án đúng ý",
    });

    // The response is the whole updated submission, so the recomputed total
    // and the trail appear without a re-fetch.
    await waitFor(() =>
      expect(screen.getByText("5 POINTS")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId(`answer-grade-trail-${QUESTION_ID}`),
    ).toHaveTextContent(/CORRECTED/);
    expect(mockedFetcher).toHaveBeenCalledTimes(1);
    expect(mockedToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ type: "success" }),
    );
  });

  test("disables the controls while a correction is in flight", async () => {
    mockedFetcher.mockResolvedValue(submission());
    let settle: (value: SubmissionDetail) => void = () => undefined;
    mockedUpdate.mockReturnValue(
      new Promise<SubmissionDetail>((resolve) => {
        settle = resolve;
      }),
    );
    await renderPage();
    await waitForEditor();

    fireEvent.change(pointsInput(), { target: { value: "3" } });
    fireEvent.change(reasonInput(), { target: { value: "Chấm lại" } });
    fireEvent.click(saveButton());

    await waitFor(() => expect(saveButton()).toBeDisabled());
    expect(saveButton()).toHaveAttribute("aria-busy", "true");
    expect(pointsInput()).toBeDisabled();
    expect(reasonInput()).toBeDisabled();

    settle(submission([answer({ points_awarded: 3 })], { total_score: 3 }));

    // The lock lifts once the write settles. The button stays disabled only
    // because an accepted correction clears the reason box, which the next
    // correction must fill in again rather than silently reusing.
    await waitFor(() => expect(reasonInput()).toBeEnabled());
    expect(pointsInput()).toBeEnabled();
    expect(saveButton()).toHaveAttribute("aria-busy", "false");
    expect(reasonInput()).toHaveValue("");
    expect(saveButton()).toBeDisabled();

    fireEvent.change(reasonInput(), { target: { value: "Chấm lại lần hai" } });
    expect(saveButton()).toBeEnabled();
    expect(mockedUpdate).toHaveBeenCalledTimes(1);
  });

  test("surfaces a 422 out-of-range refusal without crashing", async () => {
    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    mockedFetcher.mockResolvedValue(submission());
    mockedUpdate.mockRejectedValue({
      response: {
        data: {
          error_code: "GRADE_OVERRIDE_EXCEEDS_QUESTION_POINTS",
          detail: "canary-backend-detail",
          request_id: "01936ZQX9X0W7AZ2MR4BTHN5J8",
        },
      },
    });
    await renderPage();
    await waitForEditor();

    fireEvent.change(pointsInput(), { target: { value: "5" } });
    fireEvent.change(reasonInput(), { target: { value: "Chấm lại" } });
    fireEvent.click(saveButton());

    await waitFor(() =>
      expect(mockedToastAdd).toHaveBeenCalledWith({
        title: "Grade correction failed",
        description:
          "The corrected score is outside the range this question allows.",
        type: "error",
      }),
    );
    expect(consoleError).toHaveBeenCalledWith(
      "Submission grade override failed " +
        "error_code=GRADE_OVERRIDE_EXCEEDS_QUESTION_POINTS " +
        "request_id=01936ZQX9X0W7AZ2MR4BTHN5J8",
    );
    // A refused write leaves the stored score on screen, not the typed guess.
    expect(screen.getByText("0 POINTS")).toBeInTheDocument();
    expect(mockedToastAdd).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: "success" }),
    );
    expect(document.body.textContent).not.toContain("canary");
    consoleError.mockRestore();
  });

  test("surfaces a 404 cross-owner refusal without revealing which cause", async () => {
    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    mockedFetcher.mockResolvedValue(submission());
    mockedUpdate.mockRejectedValue({
      response: { data: { error_code: "SUBMISSION_NOT_FOUND" } },
    });
    await renderPage();
    await waitForEditor();

    fireEvent.change(pointsInput(), { target: { value: "2" } });
    fireEvent.change(reasonInput(), { target: { value: "Chấm lại" } });
    fireEvent.click(saveButton());

    await waitFor(() =>
      expect(mockedToastAdd).toHaveBeenCalledWith({
        title: "Grade correction failed",
        description: "The requested submission could not be found.",
        type: "error",
      }),
    );
    // The backend makes "missing" and "someone else's" indistinguishable on
    // purpose; the message must not claim which one happened.
    const description = String(
      (mockedToastAdd.mock.calls[0]?.[0] as { description?: string })
        ?.description ?? "",
    );
    expect(description).not.toMatch(/permission|owner|another teacher/i);
    // The row stays usable so a legitimate retry is possible.
    expect(saveButton()).toBeEnabled();
    consoleError.mockRestore();
  });

  test("shows the existing trail on an already-corrected answer", async () => {
    mockedFetcher.mockResolvedValue(
      submission(
        [
          answer({
            points_awarded: 4,
            is_correct: false,
            override_reason: "Học sinh diễn đạt khác nhưng đúng ý",
            overridden_at: "2026-08-19T10:00:00Z",
          }),
        ],
        { total_score: 4 },
      ),
    );
    await renderPage();
    await waitForEditor();

    const trail = screen.getByTestId(`answer-grade-trail-${QUESTION_ID}`);
    expect(trail).toHaveTextContent(/CORRECTED/);
    expect(trail).toHaveTextContent(/Học sinh diễn đạt khác nhưng đúng ý/);
  });

  test("shows no trail on an answer nobody corrected", async () => {
    mockedFetcher.mockResolvedValue(submission());
    await renderPage();
    await waitForEditor();

    expect(
      screen.queryByTestId(`answer-grade-trail-${QUESTION_ID}`),
    ).not.toBeInTheDocument();
  });

  test("keeps the grading surface square and monochrome", async () => {
    mockedFetcher.mockResolvedValue(submission());
    await renderPage();
    await waitForEditor();

    const elements = [
      screen.getByTestId(`answer-grade-editor-${QUESTION_ID}`),
      pointsInput(),
      reasonInput(),
      saveButton(),
    ];
    for (const element of elements) {
      expect(element.className).not.toMatch(
        /\b(?:bg|text|border)-(?:red|green|blue|yellow|amber|gray|slate|zinc)/,
      );
      expect(element.className).not.toMatch(/\brounded\b|\brounded-/);
    }
  });
});
