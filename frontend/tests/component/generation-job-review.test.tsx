import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";

import GenerativePreview from "@/app/(admin)/ai-workspace/GenerativePreview";
import { toast } from "@/components/ui/toast";
import {
  approveGenerationJob,
  getGenerationJob,
  publishGenerationJob,
  rejectGenerationJob,
  type AIGenerationJob,
} from "@/services/apiService";
import type { AIGenerationJobStatus } from "@/lib/ai-generation-review";

jest.mock("../../src/services/apiService", () => ({
  approveGenerationJob: jest.fn(),
  getGenerationJob: jest.fn(),
  publishGenerationJob: jest.fn(),
  rejectGenerationJob: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedApprove = jest.mocked(approveGenerationJob);
const mockedGetJob = jest.mocked(getGenerationJob);
const mockedPublish = jest.mocked(publishGenerationJob);
const mockedReject = jest.mocked(rejectGenerationJob);
const mockedToastAdd = jest.mocked(toast.add);

function job(
  status: AIGenerationJobStatus,
  overrides: Partial<AIGenerationJob> = {},
): AIGenerationJob {
  return {
    id: "job-1",
    owner_id: "teacher-1",
    material_id: "material-1",
    use_case: "question_generation",
    status,
    version: 4,
    draft_payload: null,
    failure_code: null,
    reviewer_id: null,
    created_at: "2026-08-19T00:00:00Z",
    reviewed_at: null,
    published_at: null,
    ...overrides,
  };
}

function renderPreview(
  toolArgs: Record<string, unknown> = {
    job_id: "job-1",
    status: "awaiting_review",
    questions: [{ content: "Question" }],
  },
  isStreaming = false,
) {
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <GenerativePreview
        toolName="draft_exam"
        toolArgs={toolArgs}
        isStreaming={isStreaming}
      />
    </SWRConfig>,
  );
}

const reviewPanel = () => screen.getByTestId("generation-job-review");
const statusText = () => screen.getByTestId("generation-job-status");
const button = (name: RegExp) => screen.queryByRole("button", { name });

describe("AI generation job review panel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("awaiting review offers approve and reject but never publish", async () => {
    mockedGetJob.mockResolvedValue(job("awaiting_review"));
    renderPreview();

    await waitFor(() =>
      expect(statusText()).toHaveTextContent(/ĐANG CHỜ DUYỆT/),
    );
    expect(statusText()).toHaveAttribute("data-status", "awaiting_review");
    expect(button(/^Duyệt$/)).toBeInTheDocument();
    expect(button(/^Từ chối$/)).toBeInTheDocument();
    // The backend allowlist has no `awaiting_review -> published` pair.
    expect(button(/^Xuất bản$/)).not.toBeInTheDocument();
  });

  test("approved offers publish only", async () => {
    mockedGetJob.mockResolvedValue(job("approved"));
    renderPreview();

    await waitFor(() => expect(statusText()).toHaveTextContent(/ĐÃ DUYỆT/));
    expect(button(/^Xuất bản$/)).toBeInTheDocument();
    expect(button(/^Duyệt$/)).not.toBeInTheDocument();
    expect(button(/^Từ chối$/)).not.toBeInTheDocument();
  });

  test("a rejected job offers no action at all", async () => {
    mockedGetJob.mockResolvedValue(job("rejected"));
    renderPreview();

    await waitFor(() => expect(statusText()).toHaveTextContent(/ĐÃ TỪ CHỐI/));
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(reviewPanel()).toHaveTextContent(/không thể xuất bản/i);
  });

  test.each([
    ["published", /ĐÃ XUẤT BẢN/],
    ["failed", /THẤT BẠI/],
    ["generated", /ĐANG CHUYỂN DUYỆT/],
    ["processing", /ĐANG SINH NỘI DUNG/],
  ] as [AIGenerationJobStatus, RegExp][])(
    "the %s state renders without any reviewer action",
    async (status, label) => {
      mockedGetJob.mockResolvedValue(job(status));
      renderPreview();

      await waitFor(() => expect(statusText()).toHaveTextContent(label));
      expect(screen.queryAllByRole("button")).toHaveLength(0);
    },
  );

  test("approving sends the observed version and shows the new state", async () => {
    mockedGetJob.mockResolvedValue(job("awaiting_review"));
    mockedApprove.mockResolvedValue(job("approved", { version: 5 }));
    renderPreview();

    await waitFor(() => expect(button(/^Duyệt$/)).toBeInTheDocument());
    fireEvent.click(button(/^Duyệt$/) as HTMLElement);

    await waitFor(() =>
      expect(mockedApprove).toHaveBeenCalledWith("job-1", 4),
    );
    await waitFor(() => expect(statusText()).toHaveTextContent(/ĐÃ DUYỆT/));
    // Publish becomes reachable only after the approval landed.
    expect(button(/^Xuất bản$/)).toBeInTheDocument();
    expect(mockedToastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ type: "success" }),
    );
  });

  test("rejecting sends the observed version and closes the job", async () => {
    mockedGetJob.mockResolvedValue(job("awaiting_review"));
    mockedReject.mockResolvedValue(job("rejected", { version: 5 }));
    renderPreview();

    await waitFor(() => expect(button(/^Từ chối$/)).toBeInTheDocument());
    fireEvent.click(button(/^Từ chối$/) as HTMLElement);

    await waitFor(() => expect(mockedReject).toHaveBeenCalledWith("job-1", 4));
    await waitFor(() => expect(statusText()).toHaveTextContent(/ĐÃ TỪ CHỐI/));
    expect(button(/^Xuất bản$/)).not.toBeInTheDocument();
  });

  test("publishing sends placement fields only and revalidates the job", async () => {
    mockedGetJob
      .mockResolvedValueOnce(job("approved"))
      .mockResolvedValue(job("published", { version: 6 }));
    mockedPublish.mockResolvedValue({ job_id: "job-1", status: "published" });
    renderPreview();

    await waitFor(() => expect(button(/^Xuất bản$/)).toBeInTheDocument());
    fireEvent.click(button(/^Xuất bản$/) as HTMLElement);

    await waitFor(() => expect(mockedPublish).toHaveBeenCalledTimes(1));
    expect(mockedPublish).toHaveBeenCalledWith(
      "job-1",
      { title: "AI-generated questions", topic_id: null },
      4,
    );
    await waitFor(() => expect(statusText()).toHaveTextContent(/ĐÃ XUẤT BẢN/));
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  test("disables both decisions while one is in flight", async () => {
    mockedGetJob.mockResolvedValue(job("awaiting_review"));
    let settle: (value: AIGenerationJob) => void = () => undefined;
    mockedApprove.mockReturnValue(
      new Promise<AIGenerationJob>((resolve) => {
        settle = resolve;
      }),
    );
    renderPreview();

    await waitFor(() => expect(button(/^Duyệt$/)).toBeInTheDocument());
    fireEvent.click(button(/^Duyệt$/) as HTMLElement);

    await waitFor(() => expect(button(/^Duyệt$/)).toBeDisabled());
    expect(button(/^Từ chối$/)).toBeDisabled();
    expect(button(/^Duyệt$/)).toHaveAttribute("aria-busy", "true");
    expect(button(/^Từ chối$/)).toHaveAttribute("aria-busy", "false");

    settle(job("approved", { version: 5 }));
    await waitFor(() => expect(statusText()).toHaveTextContent(/ĐÃ DUYỆT/));
    expect(mockedReject).not.toHaveBeenCalled();
  });

  test("shows a loading state before the job status is known", async () => {
    mockedGetJob.mockReturnValue(new Promise<AIGenerationJob>(() => undefined));
    renderPreview();

    expect(screen.getByRole("status")).toHaveTextContent(
      /ĐANG TẢI TRẠNG THÁI DUYỆT/,
    );
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    await Promise.resolve();
  });

  test("shows a stable error state when the job cannot be read", async () => {
    mockedGetJob.mockRejectedValue({
      response: {
        data: {
          error_code: "AI_JOB_NOT_FOUND",
          detail: "canary-backend-detail",
        },
      },
    });
    renderPreview();

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        /KHÔNG TẢI ĐƯỢC TRẠNG THÁI DUYỆT/,
      ),
    );
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(document.body.textContent).not.toContain("canary");
  });

  test("surfaces a refused decision as a localized error and keeps the state", async () => {
    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    mockedGetJob.mockResolvedValue(job("awaiting_review"));
    mockedApprove.mockRejectedValue({
      response: {
        data: {
          error_code: "AI_JOB_VERSION_CONFLICT",
          details: { provider_output: "canary-provider-secret" },
          detail: "canary-backend-detail",
          request_id: "01936ZQX9X0W7AZ2MR4BTHN5J8",
        },
      },
    });
    renderPreview();

    await waitFor(() => expect(button(/^Duyệt$/)).toBeInTheDocument());
    fireEvent.click(button(/^Duyệt$/) as HTMLElement);

    await waitFor(() =>
      expect(mockedToastAdd).toHaveBeenCalledWith({
        title: "Approval failed",
        description:
          "This AI generation job was already updated by someone else. Reload and try again.",
        type: "error",
      }),
    );
    expect(consoleError).toHaveBeenCalledWith(
      "AI generation job approve failed error_code=AI_JOB_VERSION_CONFLICT request_id=01936ZQX9X0W7AZ2MR4BTHN5J8",
    );
    expect(mockedToastAdd).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: "success" }),
    );
    // The panel re-reads rather than optimistically advancing.
    expect(statusText()).toHaveTextContent(/ĐANG CHỜ DUYỆT/);
    expect(JSON.stringify(mockedToastAdd.mock.calls)).not.toContain("canary");
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain("canary");
    consoleError.mockRestore();
  });

  test("a chat-only draft with no job offers no publish path", async () => {
    renderPreview({ questions: [{ content: "Question" }] });

    await waitFor(() =>
      expect(reviewPanel()).toHaveTextContent(/chưa gắn với phiên duyệt/i),
    );
    expect(mockedGetJob).not.toHaveBeenCalled();
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  test("hides the review panel while the draft is still streaming", () => {
    renderPreview(
      { job_id: "job-1", status: "awaiting_review", questions: [] },
      true,
    );

    expect(screen.queryByTestId("generation-job-review")).not.toBeInTheDocument();
  });

  test("keeps the review surface square and monochrome", async () => {
    mockedGetJob.mockResolvedValue(job("awaiting_review"));
    renderPreview();

    await waitFor(() => expect(button(/^Duyệt$/)).toBeInTheDocument());
    for (const element of [reviewPanel(), ...screen.getAllByRole("button")]) {
      expect(element.className).not.toMatch(
        /\b(?:bg|text|border)-(?:red|green|blue|yellow|amber|gray|slate|zinc)/,
      );
      expect(element.className).not.toMatch(/\brounded\b|\brounded-/);
    }
  });
});
