"use client";

import { AppIcon } from "@/components/ui/app-icon";

import { useState, useEffect, useRef } from "react";
import { useProfile } from "@/hooks/useProfile";
import { useStudentExams } from "@/hooks/useStudentExams";
import Link from "next/link";
import ProfileForm from "@/components/features/student-profile/ProfileForm";
import PasswordForm from "@/components/features/student-profile/PasswordForm";

export default function StudentProfilePage() {
  const { profile, isLoading: isProfileLoading } = useProfile();
  const { exams, pagination, isLoading: isExamsLoading } = useStudentExams({
    size: 100,
  });
  const [isMounted, setIsMounted] = useState(false);
  const mountedRef = useRef(false);

  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      setIsMounted(true);
    }
  }, []);

  if (!isMounted || isProfileLoading || isExamsLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center bg-white">
        <AppIcon name="sync" className="animate-spin text-black size-10" />
      </div>
    );
  }

  const completedExams = exams.filter((e) => e.submission_status === "submitted");
  const completedCount = completedExams.length;

  const normalizedScoreSum = completedExams.reduce((acc, curr) => {
    if (!curr.max_score || curr.total_score === null) return acc;
    return acc + (curr.total_score / curr.max_score) * 100;
  }, 0);
  const scoredExamCount = completedExams.filter(
    (exam) => exam.max_score && exam.total_score !== null,
  ).length;
  const averageScore = scoredExamCount > 0
    ? (normalizedScoreSum / scoredExamCount).toFixed(1)
    : "0";
  const isSummaryPartial = pagination.pages > 1;



  return (
    <div className="bg-white min-h-screen font-mono text-black p-4 md:p-8 max-w-[1200px] mx-auto w-full">
      <div className="space-y-8 mb-8">
        <ProfileForm />
        <PasswordForm />
      </div>

      {/* Grid Stats & Details */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
        {/* Stat 1: Total Completed Exams */}
        <div className="bg-white border-4 border-black p-6 shadow-[8px_8px_0_0_rgba(0,0,0,1)] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4 border-b-4 border-black pb-4">
            <span className="font-mono text-lg font-bold uppercase">
              {isSummaryPartial ? "Bài thi hoàn thành gần đây" : "Bài thi hoàn thành"}
            </span>
            <div className="w-10 h-10 border-2 border-black flex items-center justify-center">
              <AppIcon name="task_alt" className="text-black" />
            </div>
          </div>
          <div>
            <div className="text-5xl font-black text-black">{completedCount}</div>
            <p className="font-mono text-sm text-black uppercase mt-2">
              {isSummaryPartial
                ? `Trong ${exams.length} bài thi gần nhất`
                : `Trên ${pagination.total} bài thi đang công bố`}
            </p>
          </div>
        </div>

        {/* Stat 2: Average Score */}
        <div className="bg-white border-4 border-black p-6 shadow-[8px_8px_0_0_rgba(0,0,0,1)] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4 border-b-4 border-black pb-4">
            <span className="font-mono text-lg font-bold uppercase">Điểm trung bình</span>
            <div className="w-10 h-10 border-2 border-black flex items-center justify-center">
              <AppIcon name="analytics" className="text-black" />
            </div>
          </div>
          <div>
            <div className="text-5xl font-black text-black">{averageScore}%</div>
            <p className="font-mono text-sm text-black uppercase mt-2">
              Chuẩn hóa theo tổng điểm của {scoredExamCount} bài
            </p>
          </div>
        </div>

        {/* Stat 3: Role & System ID */}
        <div className="bg-white border-4 border-black p-6 shadow-[8px_8px_0_0_rgba(0,0,0,1)] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4 border-b-4 border-black pb-4">
            <span className="font-mono text-lg font-bold uppercase">Thông tin hệ thống</span>
            <div className="w-10 h-10 border-2 border-black flex items-center justify-center">
              <AppIcon name="badge" className="text-black" />
            </div>
          </div>
          <div className="space-y-2">
            <div>
              <span className="font-mono text-xs text-black uppercase block">Mã tài khoản (ID)</span>
              <span className="font-mono text-sm font-bold text-black break-all">{profile?.id}</span>
            </div>
            <div>
              <span className="font-mono text-xs text-black uppercase block">Vai trò</span>
              <span className="font-mono text-sm font-bold text-black uppercase">{profile?.role}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Completed Exams History Section */}
      <section className="bg-white border-4 border-black p-6 md:p-8 shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
        <div className="flex items-center justify-between mb-6 border-b-4 border-black pb-4">
          <h2 className="font-mono text-2xl font-black uppercase flex items-center gap-3">
            <AppIcon name="history_edu" className="text-black size-8" />
            {isSummaryPartial ? "Lịch sử thi gần đây" : "Lịch sử thi đã hoàn thành"}
          </h2>
          <span className="px-3 py-1 bg-black text-white font-mono font-bold text-sm uppercase border-2 border-black">
            {completedCount} bài thi
          </span>
        </div>

        {completedExams.length === 0 ? (
          <div className="bg-white border-2 border-dashed border-black p-8 text-center">
            <AppIcon name="find_in_page" className="size-12 text-black mb-2" />
            <p className="font-mono font-bold text-lg text-black uppercase">Chưa có bài thi nào hoàn thành</p>
            <p className="font-mono text-sm text-black uppercase mt-1">
              Hãy hoàn thành các bài thi ở trang chủ để xem lịch sử kết quả.
            </p>
            <Link
              href="/student/home"
              className="inline-block mt-4 px-6 py-3 bg-black text-white font-mono font-bold uppercase border-2 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-white hover:text-black transition-all"
            >
              Đến trang chủ
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {completedExams.map((exam) => (
              <div
                key={exam.id}
                className="bg-white border-2 border-black p-4 md:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:-translate-y-0.5 transition-all"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-0.5 bg-black text-white font-mono font-bold text-xs uppercase border border-black">
                      Đã nộp
                    </span>
                    <span className="font-mono text-xs text-black uppercase flex items-center gap-1">
                      <AppIcon name="schedule" className="size-4" />
                      {exam.duration_minutes} phút
                    </span>
                  </div>
                  <h3 className="font-mono text-xl font-bold text-black uppercase">{exam.title}</h3>
                  {exam.description && (
                    <p className="font-mono text-sm text-black line-clamp-1 mt-1">{exam.description}</p>
                  )}
                </div>

                <div className="flex items-center gap-6">
                  {exam.total_score !== null && (
                    <div className="text-right">
                      <span className="font-mono text-xs text-black uppercase block">Điểm số</span>
                      <span className="font-mono text-3xl font-black text-black">{exam.total_score}</span>
                    </div>
                  )}
                  <Link
                    href={`/student/exam/${exam.id}/result`}
                    className="px-4 py-2 bg-white text-black font-mono font-bold uppercase border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-black hover:text-white transition-all text-sm flex items-center gap-1"
                  >
                    Xem kết quả
                    <AppIcon name="arrow_forward" className="size-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
