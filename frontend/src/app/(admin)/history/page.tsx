"use client";

import React, { useState } from "react";
import { useSubmissions } from "@/hooks/useExamHistory";
import { Loader2, Search, Filter, ChevronLeft, ChevronRight, Eye } from "lucide-react";
import { useRouter } from "next/navigation";

export default function HistoryPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState("");

  const { submissions, pagination, isLoading, isError } = useSubmissions({
    page,
    size: 10,
    search,
    status,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatus(e.target.value);
    setPage(1);
  };

  return (
    <div className="p-6 bg-white min-h-screen text-black">
      <div className="mb-8 flex justify-between items-center">
        <h1 className="text-3xl font-bold font-mono uppercase tracking-tight border-b-4 border-black pb-2">Submissions History</h1>
      </div>

      <div className="mb-8 p-6 border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] flex flex-col sm:flex-row gap-4 items-end sm:items-center justify-between bg-white">
        <form onSubmit={handleSearch} className="flex gap-4 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-black" />
            <input
              type="text"
              placeholder="SEARCH BY STUDENT OR EXAM..."
              className="w-full border-2 border-black py-2 pl-10 pr-4 focus:outline-none font-mono uppercase bg-white placeholder:text-gray-400"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>
          <button type="submit" className="px-6 py-2 border-2 border-black bg-white hover:bg-black hover:text-white font-bold font-mono uppercase shadow-[4px_4px_0_0_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all">
            Search
          </button>
        </form>

        <div className="flex gap-3 items-center w-full sm:w-auto">
          <Filter className="w-5 h-5 text-black" />
          <select
            className="border-2 border-black py-2 px-4 focus:outline-none bg-white font-mono uppercase font-bold shadow-[4px_4px_0_0_rgba(0,0,0,1)] w-full sm:w-auto appearance-none cursor-pointer"
            value={status}
            onChange={handleStatusChange}
          >
            <option value="">ALL STATUSES</option>
            <option value="submitted">SUBMITTED</option>
            <option value="in_progress">IN PROGRESS</option>
            <option value="graded">GRADED</option>
          </select>
        </div>
      </div>

      <div className="border-4 border-black bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] mb-8">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b-4 border-black bg-white">
                <th className="p-4 font-bold border-r-2 border-black font-mono uppercase">Student Name</th>
                <th className="p-4 font-bold border-r-2 border-black font-mono uppercase">Exam Title</th>
                <th className="p-4 font-bold border-r-2 border-black font-mono uppercase">Score</th>
                <th className="p-4 font-bold border-r-2 border-black font-mono uppercase">Status</th>
                <th className="p-4 font-bold border-r-2 border-black font-mono uppercase">Submitted At</th>
                <th className="p-4 font-bold text-center font-mono uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center border-t-2 border-black">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-black" />
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-black font-mono uppercase font-bold border-t-2 border-black">
                    Error loading submissions.
                  </td>
                </tr>
              ) : submissions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-black font-mono uppercase font-bold border-t-2 border-black">
                    No submissions found.
                  </td>
                </tr>
              ) : (
                submissions.map((submission) => (
                  <tr key={submission.id} className="border-b-2 border-black last:border-b-0 hover:bg-black hover:text-white group transition-colors">
                    <td className="p-4 border-r-2 border-black font-mono font-bold uppercase">{submission.student_name || "UNKNOWN"}</td>
                    <td className="p-4 border-r-2 border-black font-mono uppercase">{submission.exam_title || "UNKNOWN"}</td>
                    <td className="p-4 border-r-2 border-black font-mono font-bold text-lg">
                      {submission.total_score !== undefined && submission.total_score !== null ? submission.total_score : "-"} / {submission.max_score || "-"}
                    </td>
                    <td className="p-4 border-r-2 border-black font-mono uppercase font-bold">
                      <span className="border-2 border-black px-3 py-1 bg-white text-black group-hover:shadow-[2px_2px_0_0_rgba(255,255,255,1)] shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
                        {submission.status?.replace("_", " ")}
                      </span>
                    </td>
                    <td className="p-4 font-mono font-bold uppercase border-r-2 border-black">
                      {submission.submitted_at ? new Date(submission.submitted_at).toLocaleString() : "-"}
                    </td>
                    <td className="p-4 text-center">
                      <button 
                        onClick={() => router.push(`/history/${submission.id}`)}
                        className="inline-flex items-center justify-center p-2 border-2 border-black bg-white text-black hover:invert transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)] group-hover:shadow-none"
                        title="View Details"
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

        {/* Pagination Controls */}
        {!isLoading && !isError && pagination.pages > 1 && (
          <div className="p-4 border-t-4 border-black flex items-center justify-between bg-white">
            <span className="text-sm font-bold font-mono uppercase text-black">
              PAGE {pagination.page} OF {pagination.pages} (TOTAL: {pagination.total})
            </span>
            <div className="flex gap-4">
              <button
                className="p-2 border-2 border-black bg-white text-black hover:bg-black hover:text-white disabled:opacity-50 disabled:hover:bg-white disabled:hover:text-black disabled:cursor-not-allowed shadow-[4px_4px_0_0_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all"
                disabled={pagination.page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
              <button
                className="p-2 border-2 border-black bg-white text-black hover:bg-black hover:text-white disabled:opacity-50 disabled:hover:bg-white disabled:hover:text-black disabled:cursor-not-allowed shadow-[4px_4px_0_0_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all"
                disabled={pagination.page >= pagination.pages}
                onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
