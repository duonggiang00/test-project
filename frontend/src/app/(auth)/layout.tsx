import { cookies } from "next/headers";

import { AuthSessionGuard } from "@/components/auth/AuthSessionGuard";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/auth-contract";

/**
 * Auth layout protects all routes under (auth)/.
 * Only unauthenticated users are allowed.
 * Logged-in users are redirected to their appropriate home:
 * - student -> /student/home
 * - teacher/admin -> /dashboard
 */
export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const shouldCheckSession =
    cookieStore.has(ACCESS_COOKIE) || cookieStore.has(REFRESH_COOKIE);
  return shouldCheckSession ? (
    <AuthSessionGuard>{children}</AuthSessionGuard>
  ) : (
    <>{children}</>
  );
}
