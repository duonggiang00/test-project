"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useCurrentUser } from "@/hooks/useCurrentUser";

export function AuthSessionGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, error } = useCurrentUser();

  useEffect(() => {
    if (user) {
      router.replace(user.role === "student" ? "/student/home" : "/dashboard");
    }
  }, [user, router]);

  if ((!user && !error) || user) {
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
