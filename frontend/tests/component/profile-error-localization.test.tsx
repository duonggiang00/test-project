import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import PasswordForm from "@/components/features/student-profile/PasswordForm";
import ProfileForm from "@/components/features/student-profile/ProfileForm";
import {
  updatePassword,
  updateProfile,
  useProfile,
} from "@/hooks/useProfile";

jest.mock("../../src/hooks/useProfile", () => ({
  updatePassword: jest.fn(),
  updateProfile: jest.fn(),
  uploadAvatar: jest.fn(),
  useProfile: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedUpdatePassword = jest.mocked(updatePassword);
const mockedUpdateProfile = jest.mocked(updateProfile);
const mockedUseProfile = jest.mocked(useProfile);

const rejection = (errorCode: string) => ({
  response: {
    data: {
      error_code: errorCode,
      details: {},
      request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
      detail: "canary raw profile detail",
    },
    config: { data: "canary-password" },
  },
});

describe("profile error localization", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("password form does not render rejected password data", async () => {
    mockedUpdatePassword.mockRejectedValue(
      rejection("INCORRECT_OLD_PASSWORD"),
    );
    const { container } = render(<PasswordForm />);

    for (const [name, value] of [
      ["old_password", "canary-old-password"],
      ["new_password", "canary-new-password"],
      ["confirm_password", "canary-new-password"],
    ]) {
      fireEvent.change(
        container.querySelector(`input[name="${name}"]`) as HTMLInputElement,
        { target: { value } },
      );
    }
    fireEvent.submit(container.querySelector("form") as HTMLFormElement);

    expect(
      await screen.findByText("The current password is incorrect."),
    ).toBeVisible();
    expect(container.textContent).not.toContain("canary");
  });

  test("profile form renders only the application-owned fallback", async () => {
    mockedUseProfile.mockReturnValue({
      profile: {
        id: "user-1",
        email: "student@example.test",
        role: "student",
        full_name: "Student",
        phone_number: "",
        date_of_birth: "",
        bio: "",
        avatar_url: null,
      } as never,
      user: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });
    mockedUpdateProfile.mockRejectedValue(rejection("STATE_CONFLICT"));
    const { container } = render(<ProfileForm />);

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.submit(container.querySelector("form") as HTMLFormElement);

    await waitFor(() =>
      expect(
        screen.getByText(
          "The resource is not in the required state for this action.",
        ),
      ).toBeVisible(),
    );
    expect(container.textContent).not.toContain("canary");
  });

  test("starts editing from the latest loaded profile values", () => {
    mockedUseProfile.mockReturnValue({
      profile: {
        id: "user-1",
        email: "student@example.test",
        role: "student",
        full_name: "Nguyen Student",
        phone_number: "0912345678",
        date_of_birth: "2005-01-02",
        bio: "Current profile biography",
        avatar_url: null,
      } as never,
      user: undefined,
      isLoading: false,
      isError: undefined,
      mutate: jest.fn(),
    });

    render(<ProfileForm />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByDisplayValue("Nguyen Student")).toBeVisible();
    expect(screen.getByDisplayValue("0912345678")).toBeVisible();
    expect(screen.getByDisplayValue("2005-01-02")).toBeVisible();
    expect(screen.getByDisplayValue("Current profile biography")).toBeVisible();
  });
});
