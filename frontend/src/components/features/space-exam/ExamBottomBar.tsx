import React from 'react';

export function ExamBottomBar() {
  return (
    <nav className="fixed bottom-0 left-0 w-full bg-white border-t border-black p-container-padding-mobile flex justify-between items-center z-50 rounded-t-xl">
      <button type="button" className="flex items-center gap-2 px-6 py-4 rounded-full bg-white text-black font-label-bold text-label-bold hover:bg-gray-50 transition-colors border border-black">
        <span className="material-symbols-outlined" data-icon="arrow_back">arrow_back</span>
        Câu trước
      </button>
      <button type="button" className="flex items-center gap-2 px-8 py-4 rounded-full bg-black text-white font-headline-md text-headline-md">
        Câu tiếp
        <span className="material-symbols-outlined" data-icon="arrow_forward">arrow_forward</span>
      </button>
    </nav>
  );
}
