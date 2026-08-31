import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

export function ExamBottomBar() {
  return (
    <nav className="fixed bottom-0 left-0 w-full bg-white border-t border-black p-container-padding-mobile flex justify-between items-center z-50 rounded-t-xl">
      <button type="button" className="flex items-center gap-2 px-6 py-4 rounded-full bg-white text-black font-label-bold text-label-bold hover:bg-white transition-colors border border-black">
        <AppIcon name="arrow_back" className="" data-icon="arrow_back" />
        Previous question
      </button>
      <button type="button" className="flex items-center gap-2 px-8 py-4 rounded-full bg-black text-white font-headline-md text-headline-md">
        Next question
        <AppIcon name="arrow_forward" className="" data-icon="arrow_forward" />
      </button>
    </nav>
  );
}
