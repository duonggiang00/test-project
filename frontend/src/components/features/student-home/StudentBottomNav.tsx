import React from 'react';

export default function StudentBottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 w-full z-50 bg-white border-t-4 border-black">
      <div className="flex justify-around items-center h-24 px-4 pb-4 bg-white">
        <a className="flex flex-col items-center justify-center bg-black text-white border-4 border-black px-6 py-2 shadow-[4px_4px_0_0_rgba(156,163,175,1)]" href="#">
          <span className="material-symbols-outlined">home</span>
          <span className="font-mono font-bold mt-1 uppercase">Home</span>
        </a>
        <a className="flex flex-col items-center justify-center text-black bg-white border-4 border-transparent px-6 py-2 hover:border-black hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)] transition-all" href="#">
          <span className="material-symbols-outlined">military_tech</span>
          <span className="font-mono font-bold mt-1 uppercase">Badges</span>
        </a>
        <a className="flex flex-col items-center justify-center text-black bg-white border-4 border-transparent px-6 py-2 hover:border-black hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)] transition-all" href="#">
          <span className="material-symbols-outlined">help_outline</span>
          <span className="font-mono font-bold mt-1 uppercase">Help</span>
        </a>
      </div>
    </nav>
  );
}
