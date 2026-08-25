import type { ReactNode } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import AdminLayout from "@/app/(admin)/layout";
import ExamsPage from "@/app/(admin)/exams/page";
import { Sidebar } from "@/components/features/admin/Sidebar";
import { toast } from "@/components/ui/toast";
import { createExam, useExams } from "@/hooks/useExams";
import { useTopics } from "@/hooks/useTopics";
import { useUserStore } from "@/lib/store";

const push = jest.fn();
const replace = jest.fn();
let currentSearchParams = new URLSearchParams();

jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push, replace }),
  useSearchParams: () => currentSearchParams,
}));

jest.mock("../../src/hooks/useExams", () => ({
  useExams: jest.fn(),
  createExam: jest.fn(),
  updateExam: jest.fn(),
  deleteExam: jest.fn(),
}));

jest.mock("../../src/hooks/useTopics", () => ({
  useTopics: jest.fn(),
}));

jest.mock("../../src/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    data: {
      id: "teacher-1",
      email: "teacher@example.com",
      role: "teacher",
      full_name: "Teacher One",
      is_active: true,
    },
    error: undefined,
  }),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

jest.mock("../../src/components/ui/dialog", () => ({
  Dialog: ({ open, children }: { open: boolean; children: ReactNode }) =>
    open ? <div role="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: ReactNode }) => <h2>{children}</h2>,
}));

const mockedUseExams = jest.mocked(useExams);
const mockedUseTopics = jest.mocked(useTopics);
const mockedCreateExam = jest.mocked(createExam);
const mockedToast = jest.mocked(toast.add);

const topic = {
  id: "topic-1",
  name: "Python Basics",
  description: "",
};

describe("exam creation entry flow", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    currentSearchParams = new URLSearchParams();
    useUserStore.setState({
      user: {
        id: "teacher-1",
        email: "teacher@example.com",
        role: "teacher",
        full_name: "Teacher One",
      },
    });
    mockedUseExams.mockReturnValue({
      exams: [],
      pagination: { items: [], total: 0, page: 1, size: 10, pages: 1 },
      data: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseTopics.mockReturnValue({
      topics: [topic],
      pagination: {} as never,
      data: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
  });

  test("exposes Exam Builder in desktop and mobile navigation", async () => {
    const { unmount } = render(<Sidebar />);
    expect(screen.getByRole("link", { name: /Exam Builder/i })).toHaveAttribute(
      "href",
      "/exams",
    );
    unmount();

    render(<AdminLayout><div>Dashboard content</div></AdminLayout>);
    expect(await screen.findByRole("link", { name: /Open Exam Builder/i }))
      .toHaveAttribute("href", "/exams");
  });

  test("opens Topic-backed create intent and creates a draft before redirecting", async () => {
    currentSearchParams = new URLSearchParams("topic_id=topic-1&create=1");
    mockedCreateExam.mockResolvedValue({
      id: "exam-1",
      title: "Python Quiz",
      duration_minutes: 45,
      is_published: false,
      topic_id: "topic-1",
    });

    render(<ExamsPage />);

    expect(screen.getByRole("dialog")).toBeVisible();
    expect(screen.getByTestId("exam-topic-select")).toHaveValue("topic-1");
    expect(screen.queryByTestId("exam-published-checkbox")).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId("exam-title-input"), {
      target: { value: "Python Quiz" },
    });
    fireEvent.click(screen.getByTestId("save-exam-button"));

    await waitFor(() => expect(mockedCreateExam).toHaveBeenCalledTimes(1));
    expect(mockedCreateExam).toHaveBeenCalledWith(expect.objectContaining({
      title: "Python Quiz",
      topic_id: "topic-1",
      is_published: false,
    }));
    expect(push).toHaveBeenCalledWith("/exams/exam-1");
  });

  test("clears only create intent when the Topic-backed dialog is cancelled", () => {
    currentSearchParams = new URLSearchParams("topic_id=topic-1&create=1");
    render(<ExamsPage />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(replace).toHaveBeenCalledWith("/exams?topic_id=topic-1");
    expect(mockedCreateExam).not.toHaveBeenCalled();
  });

  test("keeps the form open and reports a safe error when creation fails", async () => {
    mockedCreateExam.mockRejectedValue({
      response: {
        data: {
          error_code: "STATE_CONFLICT",
          details: {},
          detail: "canary internal detail",
        },
      },
    });
    render(<ExamsPage />);

    fireEvent.click(screen.getByTestId("add-exam-button"));
    fireEvent.change(screen.getByTestId("exam-title-input"), {
      target: { value: "Failed draft" },
    });
    fireEvent.click(screen.getByTestId("save-exam-button"));

    await waitFor(() => expect(mockedCreateExam).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("dialog")).toBeVisible();
    expect(mockedToast).toHaveBeenCalledWith(expect.objectContaining({
      type: "error",
    }));
    expect(document.body.textContent).not.toContain("canary internal detail");
  });
});
