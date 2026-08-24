"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { useTopicDetail, useTopicProgress } from "@/hooks/useTopics";
import { useTopicDecks } from "@/hooks/useFlashcards";
import { useStudentExams } from "@/hooks/useStudentExams";
import { Button } from "@/components/ui/button";
import { Search, Loader2 } from "lucide-react";
import Link from "next/link";

export default function StudentTopicDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const { id } = resolvedParams;
  const router = useRouter();

  const { topic, isLoading: isTopicLoading } = useTopicDetail(id);
  const { decks, isLoading: isDecksLoading } = useTopicDecks(id);
  
  const [searchExam, setSearchExam] = useState("");
  const [examPage, setExamPage] = useState(1);
  const { exams, pagination, isLoading: isExamsLoading } = useStudentExams({
    topic_id: id,
    search: searchExam,
    page: examPage,
    size: 4
  });

  const { progress } = useTopicProgress(id);

  if (isTopicLoading || isDecksLoading) {
    return (
      <div className="p-8 font-mono">
        <p className="text-xl font-bold uppercase">ĐANG TẢI DỮ LIỆU...</p>
      </div>
    );
  }

  if (!topic) {
    return (
      <div className="p-8 font-mono">
        <p className="text-xl font-bold uppercase">KHÔNG TÌM THẤY CHỦ ĐỀ</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 font-mono max-w-5xl mx-auto flex flex-col gap-8 w-full">
      <nav aria-label="Điều hướng chủ đề">
        <Link
          href="/student/home"
          className="inline-flex min-h-11 items-center border-4 border-black bg-white px-4 py-2 font-black uppercase shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-black hover:text-white focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-black"
        >
          &larr; Trang chủ Student
        </Link>
      </nav>
      <div className="border-4 border-black p-6 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
        <h1 className="text-3xl font-black uppercase mb-4 border-b-4 border-black pb-4">
          {topic.name}
        </h1>
        
        {/* Progress Bar Dynamic */}
        <div className="mb-6 bg-white border-4 border-black p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="font-bold uppercase">Tiến độ học tập</span>
            <span className="font-bold">{progress}%</span>
          </div>
          <div className="w-full border-4 border-black h-8 relative bg-white">
            <div className="absolute top-0 left-0 h-full bg-black transition-all duration-500" style={{ width: `${progress}%` }}></div>
          </div>
        </div>

        {topic.brief_content ? (
          <div className="prose prose-p:font-mono prose-headings:font-mono prose-a:font-mono prose-strong:font-mono max-w-none">
            <ReactMarkdown>{topic.brief_content}</ReactMarkdown>
          </div>
        ) : (
          <p className="font-bold uppercase">Chưa có nội dung tóm tắt.</p>
        )}
      </div>

      <div className="border-4 border-black p-6 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
        <h2 className="text-2xl font-black uppercase mb-6 border-b-4 border-black pb-4">
          BỘ THẺ GHI NHỚ (FLASHCARDS)
        </h2>
        {decks && decks.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {decks.map((deck) => (
              <div
                key={deck.id}
                className="border-4 border-black p-4 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] flex flex-col justify-between"
              >
                <div>
                  <h3 className="text-xl font-bold uppercase mb-2">{deck.title}</h3>
                  {deck.description && (
                    <p className="mb-4">{deck.description}</p>
                  )}
                </div>
                <Button
                  onClick={() => router.push(`/student/topics/${id}/decks/${deck.id}/study`)}
                  className="w-full border-4 border-black bg-black text-white hover:bg-white hover:text-black font-black uppercase shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:translate-x-[4px] hover:translate-y-[4px] hover:shadow-none transition-all rounded-none mt-4"
                >
                  BẮT ĐẦU ÔN TẬP
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="font-bold uppercase">CHƯA CÓ BỘ THẺ NÀO CHO CHỦ ĐỀ NÀY.</p>
        )}
      </div>
      
      {/* Exams Section */}
      <div className="border-4 border-black p-6 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 border-b-4 border-black pb-4 gap-4">
          <h2 className="text-2xl font-black uppercase">
            BÀI KIỂM TRA & ĐÁNH GIÁ
          </h2>
          <div className="relative">
            <input
              type="text"
              placeholder="TÌM BÀI THI..."
              value={searchExam}
              onChange={(e) => {
                setSearchExam(e.target.value);
                setExamPage(1);
              }}
              className="border-4 border-black px-4 py-2 w-full md:w-64 font-bold uppercase focus:outline-none focus:bg-white placeholder-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] pl-10"
            />
            <Search className="absolute left-3 top-3 w-5 h-5" />
          </div>
        </div>

        {isExamsLoading ? (
          <div className="flex justify-center p-8">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        ) : exams && exams.length > 0 ? (
          <div className="flex flex-col gap-4">
            {exams.map((exam) => {
              const isSubmitted = exam.submission_status === "submitted";
              const isInProgress = exam.submission_status === "in_progress";

              return (
                <div key={exam.id} className="border-4 border-black p-4 bg-white flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
                  <div>
                    <h3 className="font-black text-xl uppercase mb-1">{exam.title}</h3>
                    <div className="flex gap-4 text-sm font-bold uppercase">
                      <span className="bg-black text-white px-2 py-1">{exam.duration_minutes} PHÚT</span>
                    </div>
                  </div>
                  <Button
                    onClick={() => router.push(
                      isSubmitted
                        ? `/student/exam/${exam.id}/result`
                        : `/student/exam/${exam.id}`,
                    )}
                    className="border-4 border-black bg-white text-black hover:bg-black hover:text-white font-black uppercase transition-all rounded-none w-full md:w-auto"
                  >
                    {isSubmitted ? "XEM KẾT QUẢ" : isInProgress ? "TIẾP TỤC LÀM BÀI" : "BẮT ĐẦU LÀM BÀI"}
                  </Button>
                </div>
              );
            })}

            {/* Pagination Controls */}
            {pagination && pagination.pages > 1 && (
              <div className="flex justify-center gap-4 mt-6">
                <Button
                  onClick={() => setExamPage((p) => Math.max(1, p - 1))}
                  disabled={examPage === 1}
                  className="border-4 border-black bg-white text-black hover:bg-black hover:text-white font-black uppercase rounded-none disabled:opacity-50"
                >
                  TRƯỚC
                </Button>
                <span className="font-bold border-4 border-black px-4 py-2 bg-white flex items-center">
                  {examPage} / {pagination.pages}
                </span>
                <Button
                  onClick={() => setExamPage((p) => Math.min(pagination.pages, p + 1))}
                  disabled={examPage === pagination.pages}
                  className="border-4 border-black bg-white text-black hover:bg-black hover:text-white font-black uppercase rounded-none disabled:opacity-50"
                >
                  SAU
                </Button>
              </div>
            )}
          </div>
        ) : (
          <p className="font-bold uppercase text-center py-8">KHÔNG TÌM THẤY BÀI THI NÀO.</p>
        )}
      </div>
    </div>
  );
}
