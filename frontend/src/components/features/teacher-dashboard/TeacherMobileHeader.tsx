import React from 'react';

export default function TeacherMobileHeader() {
  return (
    <header className="md:hidden sticky top-0 w-full z-30 bg-white border-b border-black px-4 h-16 flex items-center justify-between">
      <h1 className="text-xl font-bold text-black">Teacher Workspace</h1>
      <button className="w-10 h-10 rounded bg-white border border-black flex items-center justify-center text-black">
        <span className="material-symbols-outlined">menu</span>
      </button>
    </header>
  );
}
