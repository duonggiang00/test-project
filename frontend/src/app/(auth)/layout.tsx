"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useUserStore } from "@/lib/store";
import { Loader2 } from "lucide-react";

/**
 * Auth Layout — protects all routes under (auth)/.
 * Only unauthenticated users are allowed.
 * Logged-in users are redirected to their appropriate home:
 * - student -> /student/dashboard
 * - teacher/admin -> /admin/dashboard
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
      <div className="flex h-screen w-full items-center justify-center bg-white">
        <Loader2 className="h-6 w-6 animate-spin text-black" />
      </div>
    );
  }

  return <>{children}</>;
}
