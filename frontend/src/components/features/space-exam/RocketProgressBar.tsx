import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

export interface RocketProgressBarProps {
  current: number;
  total: number;
}

export function RocketProgressBar({ current, total }: RocketProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (current / total) * 100));

  return (
    <div className="w-full max-w-2xl bg-white rounded-full h-8 relative overflow-visible border border-black">
      <div 
        className="bg-black border-r border-black h-full rounded-full flex items-center justify-end pr-2 relative"
        style={{ width: `${percentage}%` }}
      >
        {/* Rocket Icon acting as progress head */}
        <AppIcon name="rocket" className="text-black absolute -right-6 size-10 transform rotate-45 z-20" data-icon="rocket" />
      </div>
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 font-label-bold text-label-bold text-black mix-blend-difference whitespace-nowrap">
        Question {current} / {total}
      </div>
    </div>
  );
}
