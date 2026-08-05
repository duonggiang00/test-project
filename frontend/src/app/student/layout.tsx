"use client";

import React, { useEffect, useState } from 'react';

import { useRouter, usePathname } from 'next/navigation';
import { useUserStore } from '@/lib/store';
import { Loader2 } from 'lucide-react';
import StudentHeader from '@/components/features/student/StudentHeader';

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useUserStore();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (isMounted) {
      if (!user) {
        router.replace("/");
      } else if (user.role !== "student") {
        router.replace("/dashboard");
      }
    }
  }, [user, isMounted, router]);

  if (!isMounted) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user || user.role !== "student") {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const isExamPage = pathname?.includes('/exam/');

  return (
    <div className="min-h-screen bg-white font-mono text-black flex flex-col selection:bg-black selection:text-white">
      {!isExamPage && <StudentHeader />}
      {/* Main Content Canvas */}
      <main className="flex-1 w-full mx-auto flex flex-col">
        {children}
      </main>
    </div>
  );
}
