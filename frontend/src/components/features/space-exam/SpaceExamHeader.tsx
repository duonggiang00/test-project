import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

export function SpaceExamHeader() {
  return (
    <header className="w-full flex items-center justify-between px-container-padding-desktop h-20 max-w-[1200px] mx-auto sticky top-0 z-10 bg-white text-black">
      <div className="flex items-center gap-4">
        <button type="button" className="bg-white text-black p-3 rounded-full hover:bg-white transition-colors border border-black">
          <AppIcon name="close" className="font-label-bold text-label-bold" data-icon="close" />
        </button>
        <h1 className="font-headline-md text-headline-md text-black tracking-tight">Thử thách Không gian</h1>
      </div>
      {/* Sun Timer */}
      <div className="relative w-16 h-16 flex items-center justify-center">
        <div className="absolute inset-0 bg-white rounded-full border border-black"></div>
        <span className="font-headline-md text-headline-md text-black font-bold z-10">14</span>
      </div>
    </header>
  );
}
