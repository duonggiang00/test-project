import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
}

export function StatCard({ title, value, icon: Icon }: StatCardProps) {
  return (
    <div className="border-4 border-black bg-white p-5 flex flex-col justify-between shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
      <div className="flex justify-between items-start mb-4">
        <div className="w-10 h-10 border-2 border-black flex items-center justify-center">
          <Icon className="w-5 h-5 text-black" strokeWidth={2} />
        </div>
      </div>
      <div>
        <p className="text-sm font-bold text-black mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-black font-mono">{value}</h3>
      </div>
    </div>
  );
}
