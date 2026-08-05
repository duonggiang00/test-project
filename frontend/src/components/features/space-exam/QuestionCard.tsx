import React, { ReactNode } from 'react';
import { Image as ImageIcon } from 'lucide-react';

export interface QuestionCardProps {
  questionText: string;
  imageUrl?: string;
  children?: ReactNode;
}

export function QuestionCard({ questionText, imageUrl, children }: QuestionCardProps) {
  return (
    <article className="bg-white rounded-xl p-8 w-full max-w-3xl border border-black flex flex-col items-center text-center gap-stack-gap-md relative mt-4">
      <div className="absolute -top-12 bg-white text-black rounded-full p-4 border border-black">
        <span className="material-symbols-outlined text-4xl" data-icon="public">public</span>
      </div>
      <h2 className="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-black mt-8">
        {questionText}
      </h2>
      {imageUrl && (
        <div className="w-full h-48 md:h-64 rounded-lg mt-4 border border-black bg-gray-100 flex flex-col items-center justify-center text-gray-500 gap-2">
          <ImageIcon className="w-10 h-10 text-gray-400" />
          <span className="text-xs font-mono uppercase tracking-wider">Hình ảnh minh họa</span>
        </div>
      )}
      {children && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-stack-gap-md w-full mt-6">
          {children}
        </div>
      )}
    </article>
  );
}
