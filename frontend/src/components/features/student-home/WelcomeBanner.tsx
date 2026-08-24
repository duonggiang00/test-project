import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

interface WelcomeBannerProps {
  studentName: string;
}

export default function WelcomeBanner({ studentName }: WelcomeBannerProps) {
  return (
    <section className="relative bg-white border-4 border-black p-8 md:p-12 flex flex-col md:flex-row items-center justify-between gap-8 shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
      <div className="z-10 flex flex-col gap-4 max-w-2xl">
        <h2 className="text-3xl md:text-5xl font-black text-black uppercase tracking-tight">
          Chào buổi sáng, {studentName}!
        </h2>
        <p className="text-xl text-black font-bold border-l-4 border-black pl-4">
          Hôm nay bạn muốn khám phá vũ trụ tri thức nào?
        </p>
      </div>
      <div className="relative w-32 h-32 md:w-40 md:h-40 z-10 border-4 border-black bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] flex items-center justify-center shrink-0">
        <AppIcon name="school" className="size-16 text-black" />
      </div>
    </section>
  );
}

