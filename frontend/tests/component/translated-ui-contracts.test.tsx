import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ExamBottomBar } from "@/components/features/space-exam/ExamBottomBar";
import { QuestionCard } from "@/components/features/space-exam/QuestionCard";
import { RocketProgressBar } from "@/components/features/space-exam/RocketProgressBar";
import { SpaceExamHeader } from "@/components/features/space-exam/SpaceExamHeader";
import FeaturedExamCard from "@/components/features/student-home/FeaturedExamCard";
import TeacherDashboardScreen from "@/components/features/teacher-dashboard/TeacherDashboardScreen";
import { useConfirm } from "@/hooks/useConfirm";

function ConfirmHarness({ onResult }: { onResult: (result: boolean) => void }) {
  const { confirm, ConfirmDialog } = useConfirm();
  return (
    <>
      <button type="button" onClick={async () => onResult(await confirm("Delete this record?"))}>
        Open confirmation
      </button>
      <ConfirmDialog />
    </>
  );
}

describe("translated UI contracts", () => {
  test("renders the complete teacher dashboard copy without losing status meaning", () => {
    render(<TeacherDashboardScreen />);

    expect(screen.getByRole("heading", { name: "Dashboard Overview" })).toBeVisible();
    expect(screen.getByText("Monitor activity and AI processing progress.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Recent Exams" })).toBeVisible();
    expect(screen.getByText("Grade 10 Math Midterm")).toBeVisible();
    expect(screen.getByText("Processing")).toBeVisible();
    expect(screen.getByRole("heading", { name: "AI Processing Progress" })).toBeVisible();
    expect(screen.getByText("~2 minutes remaining")).toBeVisible();
    expect(screen.getByText("AI analysis is complete")).toBeVisible();
  });

  test("preserves exam-card destinations and action labels for every submission state", () => {
    const { rerender } = render(
      <FeaturedExamCard id="exam-1" title="New Exam" durationMinutes={30} questionCount={10} />,
    );
    expect(screen.getByRole("link", { name: "Start" })).toHaveAttribute("href", "/student/exam/exam-1");

    rerender(
      <FeaturedExamCard
        id="exam-1"
        title="New Exam"
        durationMinutes={30}
        submissionStatus="in_progress"
      />,
    );
    expect(screen.getByRole("link", { name: "Continue exam" })).toHaveAttribute("href", "/student/exam/exam-1");

    rerender(
      <FeaturedExamCard
        id="exam-1"
        title="New Exam"
        durationMinutes={30}
        submissionStatus="submitted"
        totalScore={8}
        maxScore={10}
      />,
    );
    expect(screen.getByRole("link", { name: "View result" })).toHaveAttribute("href", "/student/exam/exam-1/result");
    expect(screen.getByText(/8 \/ 10/)).toBeVisible();
  });

  test("renders translated space-exam navigation, progress, and illustration states", () => {
    render(
      <>
        <SpaceExamHeader />
        <RocketProgressBar current={4} total={5} />
        <QuestionCard questionText="Identify the planet" imageUrl="planet.png">
          <button type="button">Earth</button>
        </QuestionCard>
        <ExamBottomBar />
      </>,
    );

    expect(screen.getByRole("heading", { name: "Space Challenge" })).toBeVisible();
    expect(screen.getByText("Question 4 / 5")).toBeVisible();
    expect(screen.getByText("Question illustration")).toBeVisible();
    expect(screen.getByRole("button", { name: "Previous question" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Next question" })).toBeVisible();
  });

  test("resolves the translated confirmation dialog for confirm and cancel", async () => {
    const onResult = jest.fn();
    render(<ConfirmHarness onResult={onResult} />);

    fireEvent.click(screen.getByRole("button", { name: "Open confirmation" }));
    expect(await screen.findByRole("heading", { name: "Confirm action" })).toBeVisible();
    expect(screen.getByText("Delete this record?")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(onResult).toHaveBeenLastCalledWith(true));

    fireEvent.click(screen.getByRole("button", { name: "Open confirmation" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(onResult).toHaveBeenLastCalledWith(false));
  });
});
