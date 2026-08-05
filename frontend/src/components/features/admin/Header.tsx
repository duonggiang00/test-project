"use client";

import { useUserStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { LogOut, User } from "lucide-react";

export function Header() {
  const { user, logout } = useUserStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="flex h-16 w-full items-center justify-between border-b bg-white px-6">
      <div className="flex items-center gap-4">
        {/* Breadcrumb could go here */}
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <User className="h-4 w-4" />
          <span>{user?.full_name || "Admin"}</span>
          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">{user?.role}</span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleLogout} className="text-gray-500 hover:text-gray-900">
          <LogOut className="mr-2 h-4 w-4" />
          Đăng xuất
        </Button>
      </div>
    </header>
  );
}
