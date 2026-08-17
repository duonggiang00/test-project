"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { getBackendErrorMessage } from "@/lib/errors";
import { useUserStore } from "@/lib/store";
import { login } from "@/services/apiService";

import { AuthField } from "./AuthField";
import { AuthNotice } from "./AuthNotice";
import { AuthShell } from "./AuthShell";
import { AuthSubmitButton } from "./AuthSubmitButton";
import { PasswordField } from "./PasswordField";

type LoginFormProps = {
  registrationComplete?: boolean;
};

export function LoginForm({ registrationComplete = false }: LoginFormProps) {
  const router = useRouter();
  const { setUser } = useUserStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (registrationComplete && typeof window !== "undefined") {
      window.history.replaceState(window.history.state, "", window.location.pathname);
    }
  }, [registrationComplete]);

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isLoading) return;

    setFormError(null);
    setIsLoading(true);

    try {
      const data = await login(email, password, rememberMe);
      setUser({
        id: data.user.id,
        email: data.user.email,
        role: data.user.role,
        full_name: data.user.full_name,
      });

      router.push(
        data.user.role === "teacher" || data.user.role === "admin"
          ? "/dashboard"
          : "/student/home",
      );
    } catch (error) {
      setFormError(getBackendErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthShell
      description="Sign in to manage learning content, complete assignments, and review progress."
      eyebrow="Welcome back"
      title="Sign in"
    >
      <form className="space-y-6" onSubmit={handleLogin}>
        {registrationComplete ? (
          <AuthNotice kind="success" title="Account created">
            Your student account is ready. Sign in to continue.
          </AuthNotice>
        ) : null}

        {formError ? (
          <AuthNotice kind="error" title="Sign-in failed">
            {formError}
          </AuthNotice>
        ) : null}

        <AuthField
          autoComplete="email"
          disabled={isLoading}
          id="email"
          inputMode="email"
          label="Email"
          name="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          testId="login-email-input"
          type="email"
          value={email}
        />

        <PasswordField
          autoComplete="current-password"
          disabled={isLoading}
          id="password"
          label="Password"
          onChange={(event) => setPassword(event.target.value)}
          onToggle={() => setShowPassword((current) => !current)}
          showPassword={showPassword}
          testId="login-password-input"
          value={password}
        />

        <div className="flex flex-col gap-4 border-y-2 border-black py-4 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-black tracking-[0.08em] uppercase">
            <span className="relative flex size-6 shrink-0">
              <input
                checked={rememberMe}
                className="peer size-6 cursor-pointer appearance-none border-2 border-black bg-white outline-none checked:bg-black focus-visible:[outline:4px_solid_#000] focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:border-dashed disabled:bg-white"
                disabled={isLoading}
                id="rememberMe"
                onChange={(event) => setRememberMe(event.target.checked)}
                type="checkbox"
              />
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 hidden items-center justify-center text-sm font-black text-white peer-checked:flex"
              >
                ✓
              </span>
            </span>
            Remember me
          </label>
          <Link
            className="font-bold underline decoration-2 underline-offset-4 outline-none focus:[outline:4px_solid_#000] focus:outline-offset-2"
            href="/forgot-password"
          >
            Forgot password?
          </Link>
        </div>

        <AuthSubmitButton
          idleLabel="Sign in"
          isLoading={isLoading}
          loadingLabel="Signing in..."
          testId="login-submit-button"
        />

        <p className="border-t-2 border-black pt-5 text-center text-sm font-bold">
          Need a student account?{" "}
          <Link
            className="font-black underline decoration-2 underline-offset-4 outline-none focus:[outline:4px_solid_#000] focus:outline-offset-2"
            href="/register"
          >
            Register
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
