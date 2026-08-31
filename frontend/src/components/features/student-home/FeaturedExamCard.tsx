import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';
import Link from 'next/link';

export interface FeaturedExamCardProps {
  id: string;
  subject?: string;
  title: string;
  description?: string;
  durationMinutes: number;
  questionCount?: number;
  submissionStatus?: string | null;
  totalScore?: number | null;
  maxScore?: number;
  icon?: string;
  className?: string;
}

export default function FeaturedExamCard({
  id,
  subject = "General",
  title,
  description,
  durationMinutes,
  questionCount = 0,
  submissionStatus,
  totalScore,
  maxScore,
  icon = "description",
  className = "",
}: FeaturedExamCardProps) {
  const isSubmitted = submissionStatus === "submitted";
  const isInProgress = submissionStatus === "in_progress";

  const targetHref = isSubmitted
    ? `/student/exam/${id}/result`
    : `/student/exam/${id}`;

  return (
    <article
      data-testid={`exam-card-${title}`}
      className={`bg-white border-4 border-black p-6 flex flex-col gap-4 shadow-[4px_4px_0_0_rgba(0,0,0,1)] relative hover:-translate-y-1 hover:shadow-[8px_8px_0_0_rgba(0,0,0,1)] transition-all min-w-0 ${className}`}
    >
      {/* Top Header: Badge & Icon */}
      <div className="flex justify-between items-start">
        <div className="w-14 h-14 bg-white border-4 border-black flex items-center justify-center shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
          <AppIcon name={isSubmitted ? "task_alt" : icon} className="size-8 text-black" />
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="bg-white text-black border-2 border-black font-mono font-bold text-xs px-3 py-1 uppercase">
            {subject}
          </span>
          {isSubmitted ? (
            <span className="bg-black text-white font-mono font-bold text-xs px-2 py-0.5 uppercase border-2 border-black">
              Completed
            </span>
          ) : isInProgress ? (
            <span className="bg-white text-black font-mono font-bold text-xs px-2 py-0.5 uppercase border-2 border-black">
              In progress
            </span>
          ) : null}
        </div>
      </div>

      {/* Content */}
      <div className="flex-grow min-w-0 flex flex-col">
        <h4 className="text-xl font-bold text-black mb-2 uppercase line-clamp-2 break-all min-h-[3.5rem]">
          {title}
        </h4>
        <div className="min-h-[2.5rem]">
          {description && (
            <p className="text-sm font-medium text-black border-l-2 border-black pl-2 line-clamp-2 break-all">
              {description}
            </p>
          )}
        </div>
      </div>

      {/* Stats & Score */}
      <div className="flex items-center justify-between pt-4 border-t-4 border-black mt-auto">
        <div className="flex gap-4 text-black font-mono font-bold text-xs uppercase">
          <span className="flex items-center gap-1">
            <AppIcon name="schedule" className="size-4" /> {durationMinutes} Minutes
          </span>
          {questionCount > 0 && (
            <span className="flex items-center gap-1">
              <AppIcon name="help_outline" className="size-4" /> {questionCount} Questions
            </span>
          )}
        </div>
        {isSubmitted && totalScore !== null && totalScore !== undefined && (
          <div className="font-mono font-black text-lg text-black">
            {totalScore}{maxScore ? ` / ${maxScore}` : ""}{" "}
            <span className="text-xs uppercase font-bold">Score</span>
          </div>
        )}
      </div>

      {/* Action Button */}
      <Link href={targetHref} className="block w-full mt-2">
        <button
          data-testid={`start-exam-${title}`}
          className={`w-full h-12 font-mono font-bold text-base uppercase border-4 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] transition-all ${
            isSubmitted
              ? "bg-white text-black hover:bg-black hover:text-white"
              : "bg-black text-white hover:bg-white hover:text-black"
          }`}
        >
          {isSubmitted ? "View result" : isInProgress ? "Continue exam" : "Start"}
        </button>
      </Link>
    </article>
  );
}
