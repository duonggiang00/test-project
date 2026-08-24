import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

export default function TeacherSidebar() {
  return (
    <aside className="bg-white fixed left-0 top-0 h-screen w-[260px] border-r-4 border-black flex flex-col py-6 z-40 hidden md:flex">
      {/* Header Profile */}
      <div className="px-6 mb-8 flex items-center space-x-3">
        <div className="w-10 h-10 border-2 border-black bg-white flex items-center justify-center text-black flex-shrink-0">
          <AppIcon name="person" className="" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-black truncate font-mono">Teacher Workspace</h2>
          <p className="text-sm text-black truncate font-mono">AI Educator Pro</p>
        </div>
      </div>
      {/* Main Navigation */}
      <nav className="flex-1 px-4 space-y-2">
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-black bg-black text-white font-bold font-mono transition-none" href="#">
          <AppIcon name="dashboard" className="" style={{ fontVariationSettings: "'FILL' 1" }} />
          <span>Dashboard</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="/ai-workspace">
          <AppIcon name="workspace_premium" className="" />
          <span>AI Workspace</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <AppIcon name="quiz" className="" />
          <span>Question Bank</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <AppIcon name="construction" className="" />
          <span>Exam Builder</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-3 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <AppIcon name="bar_chart" className="" />
          <span>Reports</span>
        </a>
      </nav>

      {/* Footer Navigation */}
      <div className="mt-8 px-4 space-y-2">
        <a className="flex items-center space-x-3 px-4 py-2 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <AppIcon name="settings" className="" />
          <span>Settings</span>
        </a>
        <a className="flex items-center space-x-3 px-4 py-2 border-2 border-transparent text-black font-bold font-mono hover:bg-black hover:text-white transition-none" href="#">
          <AppIcon name="help" className="" />
          <span>Support</span>
        </a>
      </div>
    </aside>
  );
}
