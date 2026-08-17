"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { getBackendErrorMessage } from "@/lib/errors";
import { registerUser } from "@/services/apiService";

import { AuthField } from "./AuthField";
import { AuthNotice } from "./AuthNotice";
import { AuthShell } from "./AuthShell";
import { AuthSubmitButton } from "./AuthSubmitButton";
import { PasswordField } from "./PasswordField";

export function RegisterForm() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [confirmPasswordTouched, setConfirmPasswordTouched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const passwordError =
    passwordTouched && password.length < 8
      ? "Password must contain at least 8 characters."
      : undefined;
  const confirmPasswordError =
    confirmPasswordTouched && password !== confirmPassword
      ? "The passwords do not match."
      : undefined;

  const handleRegister = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isLoading) return;

    setPasswordTouched(true);
    setConfirmPasswordTouched(true);
    setFormError(null);

    if (password.length < 8 || password !== confirmPassword) return;

    setIsLoading(true);
    try {
      await registerUser({ email, password, full_name: fullName });
      router.push("/login?registered=1");
    } catch (error) {
      setFormError(getBackendErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthShell
      description="Create a student account to complete assignments, review results, and practice with flashcards."
      eyebrow="Student access"
      title="Register"
    >
      <form className="space-y-6" onSubmit={handleRegister}>
        <AuthNotice kind="info" title="Student registration">
          Self-service registration creates a student account. Teacher and admin
          access is assigned separately.
        </AuthNotice>

        {formError ? (
          <AuthNotice kind="error" title="Registration failed">
            {formError}
          </AuthNotice>
        ) : null}

        <AuthField
          autoComplete="name"
          disabled={isLoading}
          id="fullName"
          label="Full name"
          name="full_name"
          onChange={(event) => setFullName(event.target.value)}
          required
          testId="register-fullname-input"
          type="text"
          value={fullName}
        />

        <AuthField
          autoComplete="email"
          disabled={isLoading}
          id="email"
          inputMode="email"
          label="Email"
          name="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          testId="register-email-input"
          type="email"
          value={email}
        />

        <PasswordField
          autoComplete="new-password"
          disabled={isLoading}
          error={passwordError}
          hint="Use at least 8 characters."
          id="password"
          label="Password"
          onBlur={() => setPasswordTouched(true)}
          onChange={(event) => setPassword(event.target.value)}
          onToggle={() => setShowPassword((current) => !current)}
          showPassword={showPassword}
          testId="register-password-input"
          value={password}
        />

        <PasswordField
          autoComplete="new-password"
          disabled={isLoading}
          error={confirmPasswordError}
          id="confirmPassword"
          label="Confirm password"
          onBlur={() => setConfirmPasswordTouched(true)}
          onChange={(event) => setConfirmPassword(event.target.value)}
          onToggle={() => setShowConfirmPassword((current) => !current)}
          showPassword={showConfirmPassword}
          testId="register-confirm-password-input"
          value={confirmPassword}
        />

        <AuthSubmitButton
          idleLabel="Create student account"
          isLoading={isLoading}
          loadingLabel="Creating account..."
          testId="register-submit-button"
        />

        <p className="border-t-2 border-black pt-5 text-center text-sm font-bold">
          Already have an account?{" "}
          <Link
            className="font-black underline decoration-2 underline-offset-4 outline-none focus:[outline:4px_solid_#000] focus:outline-offset-2"
            href="/login"
          >
            Sign in
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
