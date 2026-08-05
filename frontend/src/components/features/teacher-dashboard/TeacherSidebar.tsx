import React from 'react';

export default function TeacherSidebar() {
  return (
    <aside className="bg-white fixed left-0 top-0 h-screen w-[260px] border-r-4 border-black flex flex-col py-6 z-40 hidden md:flex">
      {/* Header Profile */}
      <div className="px-6 mb-8 flex items-center space-x-3">
        <div className="w-10 h-10 border-2 border-black bg-white flex items-center justify-center text-black flex-shrink-0">
          <span className="material-symbols-outlined">person</span>
        </div>
        <div>
          <h2 className="text-lg font-bold text-black truncate font-mono">Teacher Workspace</h2>
          <p className="text-sm text-black truncate font-mono">AI Educator Pro</p>
        </div>
      </div>
      {/* Main Navigation */}
      <nav className="flex-1 px-4 space-y-2">
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-black bg-black text-white font-bold font-mono transition-none" href="#">
          <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>dashboard</span>
          <span>Dashboard</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="/ai-workspace">
          <span className="material-symbols-outlined">workspace_premium</span>
          <span>AI Workspace</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <span className="material-symbols-outlined">quiz</span>
          <span>Question Bank</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <span className="material-symbols-outlined">construction</span>
          <span>Exam Builder</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <span className="material-symbols-outlined">bar_chart</span>
          <span>Reports</span>
        </a>
      </nav>

      {/* Footer Navigation */}
      <div className="mt-8 px-4 space-y-2">
        <a className="flex items-center space-x-3 px-4 py-2 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <span className="material-symbols-outlined">settings</span>
          <span>Settings</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-2 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <span className="material-symbols-outlined">help</span>
          <span>Support</span>
        </a>
      </div>
    </aside>
  );
}
