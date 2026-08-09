import { Suspense } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import ForgotPasswordPage from "@/app/(auth)/forgot-password/page";
import ResetPasswordPage from "@/app/(auth)/reset-password/page";
import { toast } from "@/components/ui/toast";
import { forgotPassword, resetPassword } from "@/services/apiService";

const push = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../../src/services/apiService", () => ({
  forgotPassword: jest.fn(),
  resetPassword: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedForgotPassword = jest.mocked(forgotPassword);
const mockedResetPassword = jest.mocked(resetPassword);
const mockedToast = jest.mocked(toast.add);

const rejection = (errorCode: string) => ({
  response: {
    data: {
      error_code: errorCode,
      details: {},
      request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
      detail: "canary raw reset detail",
    },
    config: { data: "canary reset token and password" },
  },
});

describe("password recovery errors", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("reset flow localizes errors without exposing token or password", async () => {
    mockedResetPassword.mockRejectedValue(
      rejection("INVALID_OR_EXPIRED_TOKEN"),
    );
    const searchParams = Promise.resolve({ token: "canary-reset-token" });
    let container!: HTMLElement;
    await act(async () => {
      ({ container } = render(
        <Suspense fallback={<div>Loading</div>}>
          <ResetPasswordPage searchParams={searchParams} />
        </Suspense>,
      ));
      await searchParams;
    });

    fireEvent.change(
      container.querySelector("#password") as HTMLInputElement,
      { target: { value: "canary-new-password" } },
    );
    fireEvent.change(
      container.querySelector("#confirmPassword") as HTMLInputElement,
      { target: { value: "canary-new-password" } },
    );
    fireEvent.submit(container.querySelector("form") as HTMLFormElement);

    await waitFor(() =>
      expect(mockedToast).toHaveBeenCalledWith({
        title: "Password reset failed",
        description: "This link is invalid or has expired.",
        type: "error",
      }),
    );
    expect(JSON.stringify(mockedToast.mock.calls)).not.toContain("canary");
  });

  test("forgot-password flow uses a safe generic message", async () => {
    mockedForgotPassword.mockRejectedValue(rejection("INTERNAL_ERROR"));
    const { container } = render(<ForgotPasswordPage />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "canary@example.test" },
    });
    fireEvent.submit(container.querySelector("form") as HTMLFormElement);

    await waitFor(() =>
      expect(mockedToast).toHaveBeenCalledWith({
        title: "Request failed",
        description: "Something went wrong. Please try again.",
        type: "error",
      }),
    );
    expect(JSON.stringify(mockedToast.mock.calls)).not.toContain("canary");
  });
});
