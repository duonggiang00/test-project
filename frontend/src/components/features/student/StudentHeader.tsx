"use client";

import { AppIcon } from "@/components/ui/app-icon";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useRouter } from 'next/navigation';
import { useUserStore } from '@/lib/store';
import { useProfile } from '@/hooks/useProfile';
import Image from 'next/image';
import { PlayStudyBrand } from '@/components/branding/PlayStudyBrand';

export default function StudentHeader() {
  const { logout } = useUserStore();
  const { profile } = useProfile();
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    if (await logout()) router.replace("/login");
  };

  const isHome = pathname === "/student/home" || pathname === "/student";
  const isProfile = pathname === "/student/profile";

  return (
    <header className="w-full top-0 sticky bg-white border-b-4 border-black z-40">
      <div className="flex items-center justify-between gap-2 px-3 md:px-8 h-20 w-full max-w-[1200px] mx-auto">
        <Link href="/student/home" aria-label="PlayStudy student home" className="cursor-pointer">
          <PlayStudyBrand className="[&>span:last-child]:hidden sm:[&>span:last-child]:block" />
        </Link>
        <nav aria-label="Student navigation" className="flex gap-2 md:gap-8">
          <Link
            className={`font-mono text-lg font-bold flex items-center gap-2 uppercase pb-1 transition-all ${
              isHome ? "text-black border-b-4 border-black" : "text-black border-b-4 border-transparent hover:border-black"
            }`}
            href="/student/home"
          >
            <AppIcon name="home" className="" aria-hidden="true" />
            <span className="hidden sm:inline">Home</span>
          </Link>

          <Link
            className={`font-mono text-lg font-bold flex items-center gap-2 uppercase pb-1 transition-all ${
              isProfile ? "text-black border-b-4 border-black" : "text-black border-b-4 border-transparent hover:border-black"
            }`}
            href="/student/profile"
          >
            <AppIcon name="person" className="" aria-hidden="true" />
            <span className="hidden sm:inline">Profile</span>
          </Link>
        </nav>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-3">
            <span className="font-mono text-sm font-bold uppercase truncate max-w-[150px]">
              {profile?.full_name || profile?.email || "Student"}
            </span>
            <div className="w-10 h-10 border-2 border-black bg-white flex items-center justify-center overflow-hidden relative shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
              {profile?.avatar_url ? (
                <Image src={profile.avatar_url} alt="Avatar" fill className="object-cover" />
              ) : (
                <AppIcon name="person" className="size-5 text-black" />
              )}
            </div>
          </div>
          <button 
            onClick={handleLogout}
            aria-label="Log out"
            className="w-12 h-12 flex items-center justify-center bg-white border-4 border-black text-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-black hover:text-white transition-all"
            title="Sign out"
          >
            <AppIcon name="logout" className="" />
          </button>
        </div>
      </div>
    </header>
  );
}
