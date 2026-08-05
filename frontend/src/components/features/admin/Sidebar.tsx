"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUserStore } from "@/lib/store";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { href: "/topics", label: "Topic Hub", icon: "folder_special" },
  { href: "/ai-workspace", label: "AI Workspace", icon: "workspace_premium" },
  { href: "/questions", label: "Question Bank", icon: "quiz" },
  { href: "/reports", label: "Reports", icon: "bar_chart" },
  { href: "/history", label: "History", icon: "history" },
  { href: "/students", label: "Students", icon: "group" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout } = useUserStore();

  return (
    <aside className="bg-white fixed left-0 top-0 h-screen w-[260px] border-r-4 border-black flex-col py-6 z-40 hidden md:flex">
      {/* Header Profile */}
      <div className="px-6 mb-8 flex items-center space-x-3">
        <div className="w-10 h-10 border-2 border-black bg-white flex items-center justify-center text-black font-headline-sm flex-shrink-0">
          <span className="material-symbols-outlined">person</span>
        </div>
        <div>
          <h2 className="text-headline-sm font-bold text-black truncate font-mono">Teacher Workspace</h2>
          <p className="font-label-md text-label-md text-black truncate font-mono">AI Educator Pro</p>
        </div>
      </div>
      
      {/* Main Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center space-x-3 px-4 py-3 font-mono font-bold transition-none border-2",
                isActive 
                  ? "bg-black text-white border-black" 
                  : "bg-white text-black border-transparent hover:bg-black hover:text-white"
              )}
            >
              <span className="material-symbols-outlined" style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      

      
      {/* Footer Navigation */}
      <div className="mt-8 px-4 space-y-2">
        <Link href="#" className="flex items-center space-x-3 px-4 py-2 font-mono font-bold text-black bg-white border-2 border-transparent hover:bg-black hover:text-white transition-none">
          <span className="material-symbols-outlined">settings</span>
          <span>Settings</span>
        </Link>
        <Link href="#" className="flex items-center space-x-3 px-4 py-2 font-mono font-bold text-black bg-white border-2 border-transparent hover:bg-black hover:text-white transition-none">
          <span className="material-symbols-outlined">help</span>
          <span>Support</span>
        </Link>
        <button onClick={logout} className="flex w-full text-left items-center space-x-3 px-4 py-2 font-mono font-bold text-black bg-white border-2 border-transparent hover:bg-black hover:text-white transition-none">
          <span className="material-symbols-outlined">logout</span>
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
