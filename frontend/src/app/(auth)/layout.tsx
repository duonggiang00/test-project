"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useUserStore } from "@/lib/store";

/**
 * Auth layout protects all routes under (auth)/.
 * Only unauthenticated users are allowed.
 * Logged-in users are redirected to their appropriate home:
 * - student -> /student/home
 * - teacher/admin -> /dashboard
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user } = useUserStore();
  const [isMounted, setIsMounted] = useState(false);
  const mountedRef = useRef(false);

  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      setIsMounted(true);
    }
  }, []);

  useEffect(() => {
    if (!isMounted) return;
    if (user) {
      // Verify session before redirecting to prevent Next.js Middleware desync loop
      import("@/lib/api").then(({ default: api }) => {
        api.get("/auth/me")
          .then(() => {
            if (user.role === "student") {
              router.replace("/student/home");
            } else {
              router.replace("/dashboard");
            }
          })
          .catch(() => {
            // Interceptor handles clearing the user state on 401
          });
      });
    }
  }, [user, isMounted, router]);

  if (!isMounted || user) {
    return (
      <div
        className="flex min-h-dvh w-full items-center justify-center bg-white px-6 text-black"
        data-auth-surface
      >
        <div className="border-4 border-black bg-white p-6 text-center shadow-[6px_6px_0_0_#000]">
          <span
            aria-hidden="true"
            className="mx-auto block size-5 animate-pulse bg-black"
          />
          <p className="mt-4 text-sm font-black tracking-[0.16em] uppercase">
            Checking session
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
