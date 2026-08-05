import React from 'react';

export interface AnswerOptionProps {
  label: string;
  text: string;
  isSelected: boolean;
  onClick: () => void;
}

export function AnswerOption({ label, text, isSelected, onClick }: AnswerOptionProps) {
  return (
    <button 
      type="button" 
      className={`rounded-full py-4 px-6 flex items-center justify-between w-full border border-black ${isSelected ? 'bg-gray-50' : 'bg-white'}`} 
      onClick={onClick}
    >
      <span className="font-headline-md text-headline-md font-bold">{label}. {text}</span>
      <div className={`w-8 h-8 rounded-full border border-black flex items-center justify-center ${isSelected ? 'bg-black text-white' : 'bg-white'}`}>
        {isSelected && <span className="material-symbols-outlined text-sm font-bold" data-icon="check">check</span>}
      </div>
    </button>
  );
}
