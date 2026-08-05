"use client";

import React, { useState } from 'react';
import FeaturedExamCard from './FeaturedExamCard';
import { useStudentExams } from '@/hooks/useStudentExams';
import { Loader2 } from 'lucide-react';

export default function FeaturedExamList() {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 4;
  const { exams, pagination, isLoading, isError } = useStudentExams({ page: currentPage, size: itemsPerPage });

  if (isLoading) {
    return (
      <section className="flex flex-col items-center justify-center p-12 border-4 border-black bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] min-h-[300px]">
        <Loader2 className="w-12 h-12 animate-spin text-black mb-4" />
        <span className="font-mono text-lg font-bold text-black uppercase">Đang tải danh sách bài thi...</span>
      </section>
    );
  }

  if (isError) {
    return (
      <section className="flex flex-col items-center justify-center p-12 border-4 border-black bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] min-h-[300px]">
        <span className="material-symbols-outlined text-6xl text-black mb-4">error</span>
        <p className="font-mono font-bold text-black text-xl uppercase">Không thể tải danh sách bài thi</p>
        <p className="font-mono text-sm text-gray-500 uppercase mt-2">Vui lòng thử lại sau.</p>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-6 border-4 border-black p-6 md:p-8 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
      <div className="flex justify-between items-center border-b-4 border-black pb-4">
        <h3 className="text-2xl md:text-3xl font-black text-black uppercase tracking-tight flex items-center gap-3">
          <span className="material-symbols-outlined text-black text-3xl md:text-4xl">extension</span>
          Kỳ Thi Của Tôi
        </h3>
      </div>

      {exams.length === 0 ? (
        <div className="bg-white border-4 border-dashed border-black p-12 text-center flex flex-col items-center justify-center min-h-[250px]">
          <span className="material-symbols-outlined text-6xl text-black mb-4">task_alt</span>
          <p className="text-xl font-bold text-black uppercase">Bạn chưa có bài thi nào.</p>
          <p className="text-sm text-gray-500 uppercase mt-2">Hãy quay lại sau nhé!</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-6">
            {exams.map((exam) => (
              <FeaturedExamCard
                key={exam.id}
                id={exam.id}
                subject={exam.topic_name || "Tổng hợp"}
                title={exam.title}
                description={exam.description || "Bài thi đánh giá năng lực học sinh"}
                durationMinutes={exam.duration_minutes}
                questionCount={exam.question_count || 0}
                submissionStatus={exam.submission_status}
                totalScore={exam.total_score}
              />
            ))}
          </div>
          
          {/* Pagination Controls */}
          {pagination.pages > 1 && (
            <div className="flex justify-center items-center gap-4 mt-4 font-mono font-bold">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 border-4 border-black bg-white text-black hover:bg-black hover:text-white disabled:opacity-50 disabled:hover:bg-white disabled:hover:text-black transition-colors uppercase"
              >
                Trang trước
              </button>
              <span className="text-lg px-4 border-b-4 border-black">
                {currentPage} / {pagination.pages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(pagination.pages, p + 1))}
                disabled={currentPage === pagination.pages}
                className="px-4 py-2 border-4 border-black bg-white text-black hover:bg-black hover:text-white disabled:opacity-50 disabled:hover:bg-white disabled:hover:text-black transition-colors uppercase"
              >
                Trang tiếp
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

