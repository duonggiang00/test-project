import { Suspense } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";

import StudentHomePage from "@/app/student/home/page";
import StudentTopicDetailPage from "@/app/student/topics/[id]/page";
import { useProfile } from "@/hooks/useProfile";
import { useStudentExams } from "@/hooks/useStudentExams";
import { useTopicDecks } from "@/hooks/useFlashcards";
import {
  useTopicDetail,
  useTopicProgress,
  useTopics,
} from "@/hooks/useTopics";
import { useUserStore } from "@/lib/store";

const push = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));

jest.mock("../../src/hooks/useProfile", () => ({
  useProfile: jest.fn(),
}));

jest.mock("../../src/hooks/useStudentExams", () => ({
  useStudentExams: jest.fn(),
}));

jest.mock("../../src/hooks/useFlashcards", () => ({
  useTopicDecks: jest.fn(),
}));

jest.mock("../../src/hooks/useTopics", () => ({
  useTopicDetail: jest.fn(),
  useTopicProgress: jest.fn(),
  useTopics: jest.fn(),
}));

jest.mock("../../src/lib/store", () => ({
  useUserStore: jest.fn(),
}));

jest.mock(
  "../../src/components/features/student-home/FeaturedExamList",
  () => function MockFeaturedExamList() {
    return <section aria-label="My exams">Exam list</section>;
  },
);

const mockedUseProfile = jest.mocked(useProfile);
const mockedUseStudentExams = jest.mocked(useStudentExams);
const mockedUseTopicDecks = jest.mocked(useTopicDecks);
const mockedUseTopicDetail = jest.mocked(useTopicDetail);
const mockedUseTopicProgress = jest.mocked(useTopicProgress);
const mockedUseTopics = jest.mocked(useTopics);
const mockedUseUserStore = jest.mocked(useUserStore);

describe("Student flow navigation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseProfile.mockReturnValue({
      profile: undefined,
      user: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseUserStore.mockReturnValue({
      user: {
        id: "student-1",
        email: "student@example.test",
        role: "student",
        full_name: "Student User",
      },
    } as never);
    mockedUseTopics.mockReturnValue({
      topics: [],
      pagination: { items: [], total: 0, page: 1, size: 50, pages: 1 },
      data: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
  });

  test("shows the exam list and Topic library on Student Home", () => {
    render(<StudentHomePage />);

    expect(screen.getByRole("region", { name: "My exams" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Topic Library" })).toBeVisible();
  });

  test("routes exam actions by submission state", async () => {
    mockedUseTopicDetail.mockReturnValue({
      topic: {
        id: "topic-1",
        name: "Topic One",
        description: "",
        brief_content: "Brief",
      } as never,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseTopicDecks.mockReturnValue({
      decks: [],
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseTopicProgress.mockReturnValue({
      progress: 25,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUseStudentExams.mockReturnValue({
      exams: [
        { id: "exam-new", title: "New exam", duration_minutes: 30, submission_status: null },
        { id: "exam-progress", title: "Progress exam", duration_minutes: 30, submission_status: "in_progress" },
        { id: "exam-done", title: "Done exam", duration_minutes: 30, submission_status: "submitted" },
      ] as never,
      pagination: { items: [], total: 3, page: 1, size: 4, pages: 1 },
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });

    const params = Promise.resolve({ id: "topic-1" });
    await act(async () => {
      render(
        <Suspense fallback={<div>Loading</div>}>
          <StudentTopicDetailPage params={params} />
        </Suspense>,
      );
      await params;
    });

    fireEvent.click(screen.getByRole("button", { name: "START EXAM" }));
    expect(push).toHaveBeenLastCalledWith("/student/exam/exam-new");

    fireEvent.click(screen.getByRole("button", { name: "CONTINUE EXAM" }));
    expect(push).toHaveBeenLastCalledWith("/student/exam/exam-progress");

    fireEvent.click(screen.getByRole("button", { name: "VIEW RESULT" }));
    expect(push).toHaveBeenLastCalledWith("/student/exam/exam-done/result");
  });
});
