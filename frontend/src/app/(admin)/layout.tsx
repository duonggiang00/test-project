"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/features/admin/Sidebar";
import { Loader2 } from "lucide-react";
import { useCurrentUser } from "@/hooks/useCurrentUser";

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
  const { data: user, error } = useCurrentUser();
  const checkingSession = !user && !error;

  useEffect(() => {
    if (checkingSession) return;
    if (!user) {
      router.replace("/login");
    } else if (user.role === "student") {
      // Students are not allowed in the admin/teacher section
      router.replace("/student/home");
    }
  }, [user, checkingSession, router]);

  // Block render until hydration is complete (prevents localStorage mismatch)
  if (checkingSession) {
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
          <Link
            href="/exams"
            aria-label="Open Exam Builder"
            className="min-h-11 border-2 border-black bg-black px-3 font-mono text-xs font-bold text-white flex items-center justify-center hover:bg-white hover:text-black focus-visible:outline focus-visible:outline-4 focus-visible:outline-black"
          >
            EXAMS
          </Link>
        </header>
        <main className="flex-1 overflow-y-auto bg-white">
          {children}
        </main>
      </div>
    </div>
  );
}
