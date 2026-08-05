"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUserStore } from '@/lib/store';
import { useProfile } from '@/hooks/useProfile';
import Image from 'next/image';

export default function StudentHeader() {
  const { logout } = useUserStore();
  const { profile } = useProfile();
  const pathname = usePathname();

  const isHome = pathname === "/student/home" || pathname === "/student";
  const isProfile = pathname === "/student/profile";

  return (
    <header className="w-full top-0 sticky bg-white border-b-4 border-black z-40">
      <div className="flex items-center justify-between px-4 md:px-8 h-20 w-full max-w-[1200px] mx-auto">
        <Link href="/student/home" className="flex items-center gap-4 cursor-pointer">
          <div className="w-12 h-12 bg-white border-4 border-black flex items-center justify-center shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
            <span className="material-symbols-outlined text-black">face</span>
          </div>
          <h1 className="font-mono text-2xl font-black text-black tracking-tighter uppercase hidden sm:block">QuizBuddy</h1>
        </Link>
        <nav className="flex gap-4 md:gap-8">
          <Link
            className={`font-mono text-lg font-bold flex items-center gap-2 uppercase pb-1 transition-all ${
              isHome ? "text-black border-b-4 border-black" : "text-gray-400 hover:text-black hover:border-b-4 hover:border-black"
            }`}
            href="/student/home"
          >
            <span className="material-symbols-outlined">home</span> Trang chủ
          </Link>

          <Link
            className={`font-mono text-lg font-bold flex items-center gap-2 uppercase pb-1 transition-all ${
              isProfile ? "text-black border-b-4 border-black" : "text-gray-400 hover:text-black hover:border-b-4 hover:border-black"
            }`}
            href="/student/profile"
          >
            <span className="material-symbols-outlined">person</span> Trang cá nhân
          </Link>
        </nav>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-3">
            <span className="font-mono text-sm font-bold uppercase truncate max-w-[150px]">
              {profile?.full_name || profile?.email || "Học viên"}
            </span>
            <div className="w-10 h-10 border-2 border-black bg-gray-100 flex items-center justify-center overflow-hidden relative shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
              {profile?.avatar_url ? (
                <Image src={profile.avatar_url} alt="Avatar" fill className="object-cover" />
              ) : (
                <span className="material-symbols-outlined text-xl text-black">person</span>
              )}
            </div>
          </div>
          <button 
            onClick={logout}
            className="w-12 h-12 flex items-center justify-center bg-white border-4 border-black text-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-black hover:text-white transition-all"
            title="Đăng xuất"
          >
            <span className="material-symbols-outlined">logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
