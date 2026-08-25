import { render, screen, within } from "@testing-library/react";

import { metadata } from "@/app/layout";
import LandingPage from "@/app/page";
import { AuthShell } from "@/components/auth/AuthShell";
import StudentHeader from "@/components/features/student/StudentHeader";

const logout = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => "/student/home",
  useRouter: () => ({ replace: jest.fn() }),
}));

jest.mock("../../src/lib/store", () => ({
  useUserStore: () => ({ logout }),
}));

jest.mock("../../src/hooks/useProfile", () => ({
  useProfile: () => ({
    profile: {
      email: "student@example.test",
      full_name: "Test Student",
    },
  }),
}));

describe("PlayStudy branding", () => {
  test("uses the PlayStudy brand and accessible home link on the landing page", () => {
    render(<LandingPage />);

    const brandLink = screen.getByRole("link", { name: "PlayStudy home" });
    expect(within(brandLink).getByText("PlayStudy")).toBeVisible();
    expect(within(brandLink).getByTestId("playstudy-mark")).toHaveClass(
      "rounded-none",
    );
    expect(screen.getByText("© 2026 PlayStudy.")).toBeVisible();
    expect(screen.queryByText(/QuizBuddy/i)).not.toBeInTheDocument();
  });

  test("uses the same brand in the student header", () => {
    render(<StudentHeader />);

    const brandLink = screen.getByRole("link", {
      name: "PlayStudy student home",
    });
    expect(within(brandLink).getByText("PlayStudy")).toBeInTheDocument();
    expect(within(brandLink).getByTestId("playstudy-mark")).toHaveClass(
      "rounded-none",
    );
    expect(screen.queryByText(/QuizBuddy/i)).not.toBeInTheDocument();
  });

  test("uses the dark PlayStudy brand treatment in the auth shell", () => {
    render(
      <AuthShell
        eyebrow="Student access"
        title="Sign in"
        description="Access your learning workspace."
      >
        <p>Form content</p>
      </AuthShell>,
    );

    const brand = screen.getByTestId("playstudy-brand");
    expect(within(brand).getByText("PlayStudy")).toHaveClass("text-white");
    expect(within(brand).getByTestId("playstudy-mark")).toHaveClass(
      "border-white",
      "bg-white",
      "text-black",
      "rounded-none",
    );
  });

  test("publishes PlayStudy browser metadata", () => {
    expect(metadata).toMatchObject({
      applicationName: "PlayStudy",
      description:
        "A class-centered learning platform for teachers and students.",
    });
    expect(metadata.title).toEqual({
      default: "PlayStudy",
      template: "%s | PlayStudy",
    });
  });
});
