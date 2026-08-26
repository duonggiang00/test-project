import { fireEvent, render, screen } from "@testing-library/react";

import HistoryPage from "@/app/(admin)/history/page";
import { useSubmissions } from "@/hooks/useExamHistory";

const push = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../../src/hooks/useExamHistory", () => ({
  useSubmissions: jest.fn(),
}));

const mockedUseSubmissions = jest.mocked(useSubmissions);

function historyState(overrides: Record<string, unknown> = {}) {
  return {
    submissions: [{
      id: "submission-1",
      exam_id: "exam-1",
      exam_title: "Midterm",
      student_id: "student-1",
      student_name: "Alex Student",
      total_score: 8,
      max_score: 10,
      status: "in_progress",
      submitted_at: "2026-08-26T02:00:00.000Z",
    }],
    pagination: {
      items: [],
      total: 21,
      page: 1,
      size: 10,
      pages: 3,
    },
    data: undefined,
    isLoading: false,
    isError: undefined,
    mutate: jest.fn(),
    ...overrides,
  } as never;
}

describe("Submissions history", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseSubmissions.mockImplementation((params) => historyState({
      pagination: {
        items: [],
        total: 21,
        page: params?.page ?? 1,
        size: 10,
        pages: 3,
      },
    }));
  });

  test("filters, paginates, and opens a submission", () => {
    render(<HistoryPage />);
    expect(screen.getByText("Alex Student")).toBeVisible();
    expect(screen.getByText("8 / 10")).toBeVisible();
    expect(screen.getByText("in progress")).toBeVisible();

    fireEvent.change(screen.getByPlaceholderText("SEARCH BY STUDENT OR EXAM..."), {
      target: { value: "Alex" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(mockedUseSubmissions).toHaveBeenLastCalledWith({
      page: 1,
      size: 10,
      search: "Alex",
      status: "",
    });

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "graded" },
    });
    expect(mockedUseSubmissions).toHaveBeenLastCalledWith({
      page: 1,
      size: 10,
      search: "Alex",
      status: "graded",
    });

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(mockedUseSubmissions).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }));
    fireEvent.click(screen.getByRole("button", { name: "Previous page" }));
    expect(mockedUseSubmissions).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1 }));

    fireEvent.click(screen.getByTitle("View Details"));
    expect(push).toHaveBeenCalledWith("/history/submission-1");
  });

  test.each([
    ["loading", { isLoading: true }, null],
    ["error", { isError: new Error("network") }, "Error loading submissions."],
    ["empty", { submissions: [] }, "No submissions found."],
  ])("renders the %s state", (_name, overrides, expected) => {
    mockedUseSubmissions.mockReturnValue(historyState(overrides));
    render(<HistoryPage />);
    if (expected) expect(screen.getByText(expected)).toBeVisible();
    else expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  test("renders fallbacks for incomplete historical rows", () => {
    mockedUseSubmissions.mockReturnValue(historyState({
      submissions: [{
        id: "submission-2",
        exam_id: "exam-2",
        student_id: "student-2",
        total_score: null,
        max_score: 0,
        status: "submitted",
        submitted_at: null,
      }],
      pagination: { items: [], total: 1, page: 1, size: 10, pages: 1 },
    }));
    render(<HistoryPage />);
    expect(screen.getAllByText("UNKNOWN")).toHaveLength(2);
    expect(screen.getAllByText("- / -")).toHaveLength(1);
  });
});
