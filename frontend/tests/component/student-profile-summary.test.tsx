import { render, screen } from "@testing-library/react";

import StudentProfilePage from "@/app/student/profile/page";
import { useProfile } from "@/hooks/useProfile";
import { useStudentExams } from "@/hooks/useStudentExams";

jest.mock("../../src/hooks/useProfile", () => ({
  useProfile: jest.fn(),
}));

jest.mock("../../src/hooks/useStudentExams", () => ({
  useStudentExams: jest.fn(),
}));

jest.mock("../../src/components/features/student-profile/ProfileForm", () => (
  function MockProfileForm() {
    return <div>Profile form</div>;
  }
));

jest.mock("../../src/components/features/student-profile/PasswordForm", () => (
  function MockPasswordForm() {
    return <div>Password form</div>;
  }
));

const mockedUseProfile = jest.mocked(useProfile);
const mockedUseStudentExams = jest.mocked(useStudentExams);

describe("Student profile summary", () => {
  test("normalizes scores by each exam maximum", async () => {
    mockedUseProfile.mockReturnValue({
      profile: {
        id: "student-1",
        email: "student@example.test",
        full_name: "Student User",
        role: "student",
      },
      user: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseStudentExams.mockReturnValue({
      exams: [
        {
          id: "exam-1",
          title: "Exam One",
          description: null,
          duration_minutes: 30,
          submission_status: "submitted",
          total_score: 5,
          max_score: 10,
        },
        {
          id: "exam-2",
          title: "Exam Two",
          description: null,
          duration_minutes: 30,
          submission_status: "submitted",
          total_score: 8,
          max_score: 10,
        },
      ],
      pagination: { items: [], total: 2, page: 1, size: 100, pages: 1 },
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });

    render(<StudentProfilePage />);

    expect(await screen.findByText("65.0%")).toBeVisible();
    expect(screen.getByText("Trên 2 bài thi đang công bố")).toBeVisible();
  });
});
