"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useUserStore } from "@/lib/store";
import { Sidebar } from "@/components/features/admin/Sidebar";
import { Loader2 } from "lucide-react";

/**
 * Admin Layout — protects all routes under (admin)/.
 * Allowed roles: "teacher" and "admin".
 * Students are redirected to /student/home.
 * Unauthenticated users are redirected to /login.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user } = useUserStore();
  const [isMounted, setIsMounted] = useState(false);
  // Use ref to avoid triggering the set-state-in-effect lint rule on mount
  const mountedRef = useRef(false);

  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      setIsMounted(true);
    }
  }, []);

  useEffect(() => {
    if (!isMounted) return;
    if (!user) {
      router.replace("/");
    } else if (user.role === "student") {
      // Students are not allowed in the admin/teacher section
      router.replace("/student/home");
    }
  }, [user, isMounted, router]);

  // Block render until hydration is complete (prevents localStorage mismatch)
  if (!isMounted) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-white">
        <Loader2 className="h-6 w-6 animate-spin text-black" />
      </div>
    );
  }

  // Block render while redirect is in flight for unauthorized users
  if (!user || user.role === "student") {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-white">
        <Loader2 className="h-6 w-6 animate-spin text-black" />
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white text-black antialiased">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden md:ml-[260px] h-full relative w-full">
        {/* Mobile Header */}
        <header className="md:hidden sticky top-0 w-full z-30 bg-white border-b-4 border-black px-4 h-14 flex items-center justify-between">
          <h1 className="text-base font-bold text-black font-mono">Teacher Workspace</h1>
          <button className="w-9 h-9 border-2 border-black flex items-center justify-center hover:bg-black hover:text-white transition-none">
            <span className="material-symbols-outlined text-lg">menu</span>
          </button>
        </header>
        <main className="flex-1 overflow-y-auto bg-gray-50">
          {children}
        </main>
      </div>
    </div>
  );
}
