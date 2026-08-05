"use client";

import React, { use } from "react";
import { useSubmissionDetail } from "@/hooks/useExamHistory";
import { Loader2, ArrowLeft, CheckCircle2, XCircle } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

export default function HistoryDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const unwrappedParams = use(params);
  const { submission, isLoading, isError } = useSubmissionDetail(unwrappedParams.id);

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  if (isError || !submission) {
    return notFound();
  }

  return (
    <div className="p-8 bg-white text-black min-h-screen">
      <div className="max-w-4xl mx-auto space-y-12">
        
        <div className="flex items-center gap-6 border-b-4 border-black pb-6">
          <Link 
            href="/history"
            className="p-3 border-4 border-black bg-white hover:bg-black hover:text-white transition-all shadow-[4px_4px_0_0_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none flex items-center justify-center"
          >
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <div>
            <h1 className="text-4xl font-bold tracking-tight uppercase font-mono">Chi Tiết Bài Làm</h1>
            <p className="text-black font-mono font-bold mt-2 uppercase border-2 border-black inline-block px-3 py-1 shadow-[2px_2px_0_0_rgba(0,0,0,1)] bg-white">ID: {submission.id}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
            <h3 className="text-lg font-bold uppercase font-mono border-b-2 border-black pb-2 mb-4">Thông tin Sinh Viên</h3>
            <div className="space-y-4 font-mono text-lg">
              <p className="flex justify-between border-b-2 border-dashed border-gray-300 pb-2"><span>TÊN:</span> <span className="font-bold uppercase text-right">{submission.student_name}</span></p>
              <p className="flex justify-between border-b-2 border-dashed border-gray-300 pb-2"><span>EMAIL:</span> <span className="font-bold uppercase text-right">{submission.student_email}</span></p>
              <p className="flex justify-between items-center"><span>TRẠNG THÁI:</span> <span className="font-bold uppercase border-2 border-black px-3 py-1 bg-black text-white">{submission.status}</span></p>
            </div>
          </div>
          
          <div className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
            <h3 className="text-lg font-bold uppercase font-mono border-b-2 border-black pb-2 mb-4">Thông tin Đề Thi</h3>
            <div className="space-y-4 font-mono text-lg">
              <p className="flex justify-between border-b-2 border-dashed border-gray-300 pb-2"><span>ĐỀ THI:</span> <span className="font-bold uppercase text-right">{submission.exam_title}</span></p>
              <p className="flex justify-between border-b-2 border-dashed border-gray-300 pb-2 items-center"><span>ĐIỂM SỐ:</span> <span className="text-2xl font-bold border-2 border-black px-3 py-1 shadow-[2px_2px_0_0_rgba(0,0,0,1)] bg-white">{submission.total_score}</span></p>
              <p className="flex justify-between"><span>NGÀY NỘP:</span> <span className="font-bold uppercase text-right">{new Date(submission.start_time || "").toLocaleString('vi-VN')}</span></p>
            </div>
          </div>
        </div>

        <div className="mt-16">
          <h2 className="text-3xl font-bold font-mono uppercase mb-8 border-b-4 border-black pb-4 inline-block">Chi tiết Câu hỏi</h2>
          <div className="space-y-8">
            {submission.answers && submission.answers.length > 0 ? (
              submission.answers.map((ans, idx) => (
                <div key={ans.question_id} className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
                  <div className="flex flex-col sm:flex-row items-start justify-between mb-6 gap-4">
                    <h4 className="font-bold text-xl font-mono uppercase leading-relaxed"><span className="bg-black text-white px-3 py-1 mr-3 border-2 border-black inline-block mb-2 sm:mb-0">CÂU {idx + 1}</span> {ans.question_content}</h4>
                    <div className="flex items-center gap-4 shrink-0">
                      <span className="font-bold font-mono text-lg border-2 border-black px-4 py-2 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] uppercase whitespace-nowrap">
                        {ans.points_awarded} ĐIỂM
                      </span>
                      {ans.is_correct ? (
                        <div className="bg-white border-2 border-black p-1 shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
                          <CheckCircle2 className="w-10 h-10 text-black" />
                        </div>
                      ) : (
                        <div className="bg-black border-2 border-black p-1 shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-white">
                          <XCircle className="w-10 h-10" />
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="mt-6 p-6 border-2 border-black bg-gray-100 shadow-inner">
                    <p className="text-lg font-bold font-mono uppercase text-black mb-4 border-b-2 border-black pb-2 inline-block">DỮ LIỆU BÀI LÀM:</p>
                    <pre className="whitespace-pre-wrap font-mono text-base bg-white border-2 border-black p-4 overflow-x-auto shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
                      {JSON.stringify(ans.answer_data, null, 2)}
                    </pre>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-12 border-4 border-black border-dashed text-center text-black font-bold font-mono text-xl uppercase bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
                KHÔNG CÓ DỮ LIỆU CÂU TRẢ LỜI
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
