import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { LoginForm } from "@/components/auth/LoginForm";
import { RegisterForm } from "@/components/auth/RegisterForm";
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

const mockedLogin = jest.mocked(login);
const mockedRegister = jest.mocked(registerUser);

const fillLoginForm = () => {
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "user@example.test" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "secure-password" },
  });
};

const fillRegistrationForm = ({
  password = "secure-password",
  confirmation = password,
}: {
  password?: string;
  confirmation?: string;
} = {}) => {
  fireEvent.change(screen.getByLabelText("Full name"), {
    target: { value: "Test Student" },
  });
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "student@example.test" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: password },
  });
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value: confirmation },
  });
};

describe("authentication forms", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.history.replaceState({}, "", "/login");
  });

  test("exposes complete login navigation and toggles password visibility", () => {
    render(<LoginForm />);

    const password = screen.getByLabelText("Password");
    expect(screen.getByLabelText("Email")).toHaveAttribute("autocomplete", "email");
    expect(password).toHaveAttribute("autocomplete", "current-password");
    expect(password).toHaveAttribute("type", "password");
    expect(screen.getByRole("link", { name: "Forgot password?" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
    expect(screen.getByRole("link", { name: "Register" })).toHaveAttribute(
      "href",
      "/register",
    );

    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(password).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Hide password" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  test.each([
    ["admin", "/dashboard"],
    ["teacher", "/dashboard"],
    ["student", "/student/home"],
  ])("redirects a %s after login", async (role, destination) => {
    mockedLogin.mockResolvedValue({
      user: {
        id: `${role}-id`,
        email: `${role}@example.test`,
        role,
        full_name: `Test ${role}`,
      },
    });
    render(<LoginForm />);
    fillLoginForm();

    if (role === "admin") {
      fireEvent.click(screen.getByRole("checkbox", { name: "Remember me" }));
    }
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith(destination));
    expect(mockedLogin).toHaveBeenCalledWith(
      "user@example.test",
      "secure-password",
      role === "admin",
    );
    expect(setUser).toHaveBeenCalledWith(expect.objectContaining({ role }));
  });

  test("disables the login form and prevents duplicate submissions", async () => {
    let resolveLogin: ((value: unknown) => void) | undefined;
    mockedLogin.mockReturnValue(
      new Promise((resolve) => {
        resolveLogin = resolve;
      }) as ReturnType<typeof login>,
    );
    render(<LoginForm />);
    fillLoginForm();

    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    const loadingButton = screen.getByRole("button", { name: "Signing in..." });
    expect(loadingButton).toBeDisabled();
    fireEvent.click(loadingButton);
    expect(mockedLogin).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveLogin?.({
        user: {
          id: "student-id",
          email: "student@example.test",
          role: "student",
          full_name: "Test Student",
        },
      });
    });
  });

  test("validates password length and confirmation next to the fields", () => {
    render(<RegisterForm />);
    fillRegistrationForm({ password: "short", confirmation: "different" });

    fireEvent.click(
      screen.getByRole("button", { name: "Create student account" }),
    );

    expect(screen.getByText("Password must contain at least 8 characters.")).toBeVisible();
    expect(screen.getByText("The passwords do not match.")).toBeVisible();
    expect(mockedRegister).not.toHaveBeenCalled();
  });

  test("registers only the supported student payload and returns to login", async () => {
    mockedRegister.mockResolvedValue({ id: "student-id" });
    render(<RegisterForm />);
    fillRegistrationForm();

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "autocomplete",
      "new-password",
    );
    expect(screen.getByLabelText("Confirm password")).toHaveAttribute(
      "autocomplete",
      "new-password",
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Create student account" }),
    );

    await waitFor(() =>
      expect(mockedRegister).toHaveBeenCalledWith({
        email: "student@example.test",
        password: "secure-password",
        full_name: "Test Student",
      }),
    );
    expect(push).toHaveBeenCalledWith("/login?registered=1");
  });

  test("shows the one-time registration notice and removes its query marker", async () => {
    window.history.replaceState({}, "", "/login?registered=1");
    render(<LoginForm registrationComplete />);

    expect(screen.getByRole("status")).toHaveTextContent("Account created");
    await waitFor(() => expect(window.location.search).toBe(""));
  });
});
