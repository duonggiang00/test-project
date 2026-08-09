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

jest.mock(
  "../../src/components/features/student/BrutalistMatchingUI",
  () => () => null,
);

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
        questions: [],
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
});
