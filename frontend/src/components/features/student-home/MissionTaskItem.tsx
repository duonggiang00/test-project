import React from 'react';

interface MissionTaskItemProps {
  title: string;
  current: number;
  total: number;
  isCompleted: boolean;
}

export default function MissionTaskItem({ title, current, total, isCompleted }: MissionTaskItemProps) {
  const progressPercent = Math.min(100, Math.round((current / total) * 100));
  
  return (
    <div className="flex items-center gap-4 bg-white p-3 border-2 border-black hover:bg-black hover:text-white transition-none group cursor-pointer">
      <div className={`w-8 h-8 flex items-center justify-center shrink-0 bg-white border-2 border-black group-hover:border-white`}>
        <span className={`material-symbols-outlined text-black group-hover:text-white font-bold`}>
          {isCompleted ? 'check' : ''}
        </span>
      </div>
      <div className="flex-grow">
        <p className="font-bold text-black group-hover:text-white font-mono">{title}</p>
        <div className="w-full h-3 bg-white border-2 border-black mt-2 overflow-hidden relative group-hover:border-white">
          <div 
            className={`h-full bg-black group-hover:bg-white`} 
            style={{ width: `${progressPercent}%` }}
          >
          </div>
        </div>
      </div>
      {!isCompleted && (
        <span className="font-bold text-black group-hover:text-white font-mono text-sm">{current}/{total}</span>
      )}
    </div>
  );
}
