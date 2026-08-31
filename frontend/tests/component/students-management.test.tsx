import { Suspense } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import StudentProfilePage from "@/app/(admin)/students/[id]/page";
import StudentsPage from "@/app/(admin)/students/page";
import { useSubmissions } from "@/hooks/useExamHistory";
import { useConfirm } from "@/hooks/useConfirm";
import {
  deleteUser,
  updateUserRole,
  useUserDetail,
  useUsers,
} from "@/hooks/useUsers";
import { logBackendError } from "@/lib/errors";

const push = jest.fn();
const notFound = jest.fn(() => <div>NOT FOUND</div>);

jest.mock("next/navigation", () => ({
  notFound: () => notFound(),
  useRouter: () => ({ push }),
}));

jest.mock("../../src/hooks/useUsers", () => ({
  deleteUser: jest.fn(),
  updateUserRole: jest.fn(),
  useUserDetail: jest.fn(),
  useUsers: jest.fn(),
}));

jest.mock("../../src/hooks/useExamHistory", () => ({
  useSubmissions: jest.fn(),
}));

jest.mock("../../src/hooks/useConfirm", () => ({
  useConfirm: jest.fn(),
}));

jest.mock("../../src/lib/errors", () => ({
  logBackendError: jest.fn(),
}));

const mockedDeleteUser = jest.mocked(deleteUser);
const mockedLogBackendError = jest.mocked(logBackendError);
const mockedUpdateUserRole = jest.mocked(updateUserRole);
const mockedUseConfirm = jest.mocked(useConfirm);
const mockedUseSubmissions = jest.mocked(useSubmissions);
const mockedUseUserDetail = jest.mocked(useUserDetail);
const mockedUseUsers = jest.mocked(useUsers);
const confirm = jest.fn();
const mutate = jest.fn();

function usersState(overrides: Record<string, unknown> = {}) {
  return {
    users: [{
      id: "student-1",
      email: "student@example.test",
      full_name: "Alex Student",
      role: "student",
    }],
    data: undefined,
    isLoading: false,
    isError: undefined,
    mutate,
    ...overrides,
  } as never;
}

function submissionsState(overrides: Record<string, unknown> = {}) {
  return {
    submissions: [
      {
        id: "submission-1",
        exam_id: "exam-1",
        exam_title: "Midterm",
        student_id: "student-1",
        total_score: 8,
        max_score: 10,
        status: "graded",
        submitted_at: "2026-08-26T02:00:00.000Z",
      },
      {
        id: "submission-2",
        exam_id: "exam-2",
        exam_title: null,
        student_id: "student-1",
        total_score: 4,
        max_score: 0,
        status: "submitted",
        submitted_at: null,
      },
    ],
    pagination: { items: [], total: 2, page: 1, size: 50, pages: 1 },
    data: undefined,
    isLoading: false,
    isError: undefined,
    mutate: jest.fn(),
    ...overrides,
  } as never;
}

async function renderProfile() {
  const params = Promise.resolve({ id: "student-1" });
  await act(async () => {
    render(
      <Suspense fallback={<div>Resolving profile</div>}>
        <StudentProfilePage params={params} />
      </Suspense>,
    );
    await params;
  });
}

describe("Students management", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    confirm.mockResolvedValue(true);
    mockedUseConfirm.mockReturnValue({
      confirm,
      ConfirmDialog: () => <div data-testid="confirm-dialog" />,
    });
    mockedUseUsers.mockReturnValue(usersState());
    mockedUseUserDetail.mockReturnValue({
      user: {
        id: "student-1",
        email: "student@example.test",
        full_name: "Alex Student",
        role: "student",
        created_at: "2026-08-01T00:00:00.000Z",
      } as never,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseSubmissions.mockReturnValue(submissionsState());
  });

  test("updates a role and deletes a confirmed user", async () => {
    mockedUpdateUserRole.mockResolvedValue({} as never);
    mockedDeleteUser.mockResolvedValue(undefined as never);
    render(<StudentsPage />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "teacher" } });
    await waitFor(() => expect(mockedUpdateUserRole).toHaveBeenCalledWith(
      "student-1",
      "teacher",
    ));

    await waitFor(() => expect(screen.getByTitle("Delete User")).toBeEnabled());
    fireEvent.click(screen.getByTitle("Delete User"));
    await waitFor(() => expect(confirm).toHaveBeenCalledWith(
      "Are you sure you want to delete this user?",
    ));
    expect(mockedDeleteUser).toHaveBeenCalledWith("student-1");
    expect(mutate).toHaveBeenCalledTimes(2);
  });

  test("keeps the list stable when role or delete operations fail", async () => {
    mockedUpdateUserRole.mockRejectedValue(new Error("role failed"));
    mockedDeleteUser.mockRejectedValue(new Error("delete failed"));
    render(<StudentsPage />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "admin" } });
    await waitFor(() => expect(mockedLogBackendError).toHaveBeenCalledWith(
      "User role update failed",
      expect.any(Error),
    ));
    await waitFor(() => expect(screen.getByTitle("Delete User")).toBeEnabled());
    fireEvent.click(screen.getByTitle("Delete User"));
    await waitFor(() => expect(mockedLogBackendError).toHaveBeenCalledWith(
      "User delete failed",
      expect.any(Error),
    ));
    expect(screen.getByText("student@example.test")).toBeVisible();
  });

  test("does not delete a user when confirmation is declined", async () => {
    confirm.mockResolvedValue(false);
    render(<StudentsPage />);
    fireEvent.click(screen.getByTitle("Delete User"));
    await waitFor(() => expect(confirm).toHaveBeenCalled());
    expect(mockedDeleteUser).not.toHaveBeenCalled();
  });

  test.each([
    ["loading", { isLoading: true }, "Loading users..."],
    ["empty", { users: [] }, "No users found."],
  ])("renders the %s list state", (_name, overrides, expected) => {
    mockedUseUsers.mockReturnValue(usersState(overrides));
    render(<StudentsPage />);
    expect(screen.getByText(expected)).toBeVisible();
  });

  test("renders profile statistics, history fallbacks, and detail navigation", async () => {
    await renderProfile();
    expect(mockedUseUserDetail).toHaveBeenCalledWith("student-1");
    expect(mockedUseSubmissions).toHaveBeenCalledWith({
      student_id: "student-1",
      size: 50,
    });
    expect(screen.getByRole("heading", { name: "Alex Student" })).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    expect(screen.getByText("6.0")).toBeVisible();
    expect(screen.getByText("Unknown")).toBeVisible();
    expect(screen.getByText("4 / -")).toBeVisible();
    fireEvent.click(screen.getAllByTitle("View grading details")[0]);
    expect(push).toHaveBeenCalledWith("/history/submission-1");
  });

  test("renders loading and empty-history profile states", async () => {
    mockedUseSubmissions.mockReturnValue(submissionsState({
      submissions: [],
      isLoading: true,
    }));
    await renderProfile();
    expect(screen.getByText("Loading...")).toBeVisible();

    mockedUseSubmissions.mockReturnValue(submissionsState({ submissions: [] }));
    const params = Promise.resolve({ id: "student-1" });
    await act(async () => {
      render(
        <Suspense fallback={<div>Resolving profile</div>}>
          <StudentProfilePage params={params} />
        </Suspense>,
      );
      await params;
    });
    expect(screen.getByText("This student has not completed any exams.")).toBeVisible();
  });

  test("delegates a missing profile to the framework not-found boundary", async () => {
    mockedUseUserDetail.mockReturnValue({
      user: undefined,
      isLoading: false,
      isError: new Error("missing"),
      mutate: jest.fn(),
    });
    await renderProfile();
    expect(notFound).toHaveBeenCalledTimes(1);
    expect(screen.getByText("NOT FOUND")).toBeVisible();
  });

  test("renders the profile loading boundary", async () => {
    mockedUseUserDetail.mockReturnValue({
      user: undefined,
      isLoading: true,
      isError: undefined,
      mutate: jest.fn(),
    });
    await renderProfile();
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });
});
