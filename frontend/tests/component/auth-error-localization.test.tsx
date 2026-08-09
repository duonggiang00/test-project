import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import LoginPage from "@/app/(auth)/login/page";
import RegisterPage from "@/app/(auth)/register/page";
import { toast } from "@/components/ui/toast";
import { login, registerUser } from "@/services/apiService";

const push = jest.fn();
const setUser = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../../src/lib/store", () => ({
  useUserStore: () => ({ setUser }),
}));

jest.mock("../../src/services/apiService", () => ({
  login: jest.fn(),
  registerUser: jest.fn(),
}));

jest.mock("../../src/components/ui/toast", () => ({
  toast: { add: jest.fn() },
}));

const mockedLogin = jest.mocked(login);
const mockedRegister = jest.mocked(registerUser);
const mockedToast = jest.mocked(toast.add);

const canonicalError = (errorCode: string) => ({
  response: {
    data: {
      error_code: errorCode,
      details: {},
      request_id: "8f37b4ca-2014-4cec-aa2d-3f967c27eb8e",
      detail: "canary raw backend detail",
    },
    config: { data: "canary-password" },
  },
});

describe("authentication error localization", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("login does not expose the rejected credential payload", async () => {
    mockedLogin.mockRejectedValue(canonicalError("INVALID_CREDENTIALS"));
    render(<LoginPage />);

    fireEvent.change(screen.getByTestId("login-email-input"), {
      target: { value: "teacher@example.test" },
    });
    fireEvent.change(screen.getByTestId("login-password-input"), {
      target: { value: "canary-password" },
    });
    fireEvent.click(screen.getByTestId("login-submit-button"));

    await waitFor(() =>
      expect(mockedToast).toHaveBeenCalledWith({
        title: "Login failed",
        description: "The email address or password is incorrect.",
        type: "error",
      }),
    );
    expect(JSON.stringify(mockedToast.mock.calls)).not.toContain("canary");
  });

  test("registration does not expose the Axios request body", async () => {
    mockedRegister.mockRejectedValue(canonicalError("USER_ALREADY_EXISTS"));
    render(<RegisterPage />);

    fireEvent.change(screen.getByTestId("register-fullname-input"), {
      target: { value: "Test Student" },
    });
    fireEvent.change(screen.getByTestId("register-email-input"), {
      target: { value: "student@example.test" },
    });
    fireEvent.change(screen.getByTestId("register-password-input"), {
      target: { value: "canary-password" },
    });
    fireEvent.change(screen.getByTestId("register-confirm-password-input"), {
      target: { value: "canary-password" },
    });
    fireEvent.click(screen.getByTestId("register-submit-button"));

    await waitFor(() =>
      expect(mockedToast).toHaveBeenCalledWith({
        title: "Registration failed",
        description: "This email address is already in use.",
        type: "error",
      }),
    );
    expect(JSON.stringify(mockedToast.mock.calls)).not.toContain("canary");
  });
});
