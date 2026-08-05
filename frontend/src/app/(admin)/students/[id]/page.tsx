"use client";

import React, { use } from "react";
import { useUserDetail } from "@/hooks/useUsers";
import { useSubmissions } from "@/hooks/useExamHistory";
import { Loader2, ArrowLeft, Eye, Mail, User as UserIcon, Calendar } from "lucide-react";
import Link from "next/link";
import { notFound, useRouter } from "next/navigation";

export default function StudentProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const unwrappedParams = use(params);
  const router = useRouter();
  
  // Lấy thông tin user
  const { user, isLoading: isLoadingUser, isError: isUserError } = useUserDetail(unwrappedParams.id);
  
  // Lấy danh sách lịch sử thi của user này
  const { submissions, isLoading: isLoadingSubmissions } = useSubmissions({ student_id: unwrappedParams.id, size: 50 });

  if (isLoadingUser) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-black" />
      </div>
    );
  }

  if (isUserError || !user) {
    return notFound();
  }

  // Tính toán thống kê cơ bản
  const totalExams = submissions.length;
  const gradedExams = submissions.filter(s => s.status === 'graded' || s.status === 'submitted');
  const totalScore = gradedExams.reduce((acc, curr) => acc + (curr.total_score || 0), 0);
  const averageScore = gradedExams.length > 0 ? (totalScore / gradedExams.length).toFixed(1) : "-";

  return (
    <div className="p-6 lg:p-8 bg-white text-black min-h-screen">
      <div className="flex items-center gap-6 border-b-4 border-black pb-6 mb-8">
        <Link 
          href="/students"
          className="p-3 border-4 border-black bg-white hover:bg-black hover:text-white transition-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] flex items-center justify-center"
        >
          <ArrowLeft className="w-6 h-6" />
        </Link>
        <div>
          <h1 className="text-4xl font-bold uppercase font-mono tracking-tight">Hồ Sơ Học Viên</h1>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cột trái: Thông tin cá nhân */}
        <div className="lg:col-span-1 space-y-8">
          <div className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
            <div className="flex justify-center mb-6">
              <div className="w-32 h-32 border-4 border-black bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] flex items-center justify-center">
                <UserIcon className="w-16 h-16 text-black" />
              </div>
            </div>
            <h2 className="text-2xl font-bold font-mono uppercase text-center mb-6 border-b-4 border-black pb-4">{user.full_name || "Chưa cập nhật"}</h2>
            
            <div className="space-y-4 font-mono font-bold uppercase text-sm">
              <div className="flex items-center gap-3">
                <Mail className="w-6 h-6 text-black shrink-0" />
                <span className="break-all">{user.email}</span>
              </div>
              <div className="flex items-center gap-3">
                <UserIcon className="w-6 h-6 text-black shrink-0" />
                <span className="border-2 border-black px-2 py-1 bg-white text-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]">{user.role}</span>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="w-6 h-6 text-black shrink-0" />
                <span>Tham gia: {user.created_at ? new Date(user.created_at).toLocaleDateString('vi-VN') : "-"}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="border-4 border-black p-4 text-center bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
              <p className="text-xs font-bold font-mono uppercase text-black mb-2 border-b-2 border-black pb-2">Tổng bài thi</p>
              <p className="text-4xl font-mono font-bold">{totalExams}</p>
            </div>
            <div className="border-4 border-black p-4 text-center bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
              <p className="text-xs font-bold font-mono uppercase text-black mb-2 border-b-2 border-black pb-2">Điểm trung bình</p>
              <p className="text-4xl font-mono font-bold">{averageScore}</p>
            </div>
          </div>
        </div>

        {/* Cột phải: Lịch sử thi */}
        <div className="lg:col-span-2">
          <div className="flex justify-between items-center mb-6 border-b-4 border-black pb-4">
            <h2 className="text-3xl font-mono font-bold uppercase">Lịch sử Làm bài</h2>
          </div>

          <div className="border-4 border-black bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b-4 border-black bg-white uppercase text-xs tracking-wider">
                    <th className="p-4 font-mono font-bold border-r-4 border-black">Tên Đề Thi</th>
                    <th className="p-4 font-mono font-bold border-r-4 border-black">Điểm</th>
                    <th className="p-4 font-mono font-bold border-r-4 border-black">Trạng thái</th>
                    <th className="p-4 font-mono font-bold border-r-4 border-black">Ngày nộp</th>
                    <th className="p-4 font-mono font-bold text-center">Chi tiết</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoadingSubmissions ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center font-mono font-bold uppercase">
                        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-black" />
                        Đang tải...
                      </td>
                    </tr>
                  ) : submissions.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-black font-mono font-bold uppercase text-lg">
                        Học viên chưa làm bài thi nào.
                      </td>
                    </tr>
                  ) : (
                    submissions.map((submission) => (
                      <tr key={submission.id} className="border-b-4 border-black last:border-b-0 bg-white">
                        <td className="p-4 border-r-4 border-black font-mono font-bold">{submission.exam_title || "Unknown"}</td>
                        <td className="p-4 border-r-4 border-black font-mono font-bold">
                          {submission.total_score !== undefined && submission.total_score !== null ? submission.total_score : "-"} / {submission.max_score || "-"}
                        </td>
                        <td className="p-4 border-r-4 border-black font-mono text-center">
                          <span className={`inline-block px-2 py-1 text-xs font-bold uppercase border-2 border-black bg-white text-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]`}>
                            {submission.status?.replace("_", " ")}
                          </span>
                        </td>
                        <td className="p-4 border-r-4 border-black font-mono text-sm font-bold">
                          {submission.submitted_at ? new Date(submission.submitted_at).toLocaleString('vi-VN') : "-"}
                        </td>
                        <td className="p-4 text-center">
                          <button 
                            onClick={() => router.push(`/history/${submission.id}`)}
                            className="inline-flex items-center justify-center p-2 border-2 border-black bg-white hover:bg-black hover:text-white transition-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]"
                            title="Xem chi tiết chấm bài"
                          >
                            <Eye className="w-5 h-5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
