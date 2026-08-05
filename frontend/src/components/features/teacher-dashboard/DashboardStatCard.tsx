import React from 'react';

interface DashboardStatCardProps {
  icon: string;
  iconBgClass?: string;
  iconTextClass?: string;
  trend?: {
    type: 'up' | 'down';
    value: string;
    bgClass?: string;
    textClass?: string;
    icon: string;
  };
  title: string;
  value: string;
}

export default function DashboardStatCard({
  icon,
  trend,
  title,
  value,
}: DashboardStatCardProps) {
  return (
    <div className="bg-white border-4 border-black p-5 flex flex-col justify-between shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
      <div className="flex justify-between items-start mb-4">
        <div className="w-10 h-10 flex items-center justify-center border-2 border-black bg-white text-black">
          <span className="material-symbols-outlined">{icon}</span>
        </div>
        {trend && (
          <span className="text-xs font-bold flex items-center px-2 py-1 border-2 border-black bg-white text-black font-mono">
            <span className="material-symbols-outlined text-[14px] mr-1">{trend.icon}</span> {trend.value}
          </span>
        )}
      </div>
      <div>
        <p className="text-sm font-bold text-black uppercase tracking-tight mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-black font-mono">{value}</h3>
      </div>
    </div>
  );
}
