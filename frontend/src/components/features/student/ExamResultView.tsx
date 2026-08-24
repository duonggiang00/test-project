"use client";

import React from "react";
import BrutalistMatchingUI, { MatchPair as MatchPairType } from "@/components/features/student/BrutalistMatchingUI";
import { useRouter } from "next/navigation";
import { useStudentExamResult } from "@/hooks/useStudentExams";
import { ArrowLeft, CheckCircle, XCircle, Loader2 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

type MatchPair = MatchPairType;

type BlankAnswer = {
  blank_index?: number;
  acceptable_answers?: string[];
};

function parseAnswerData(answerData: unknown): Record<string, unknown> | null {
  if (!answerData) return null;
  if (typeof answerData === "string") {
    try {
      return JSON.parse(answerData) as Record<string, unknown>;
    } catch {
      return null;
    }
  }
  if (typeof answerData === "object") {
    return answerData as Record<string, unknown>;
  }
  return null;
}

function getSelectedOptionIds(answerData: unknown): string[] {
  const parsed = parseAnswerData(answerData);
  if (!parsed) return [];
  if (Array.isArray(parsed.selected_option_ids)) {
    return (parsed.selected_option_ids as unknown[]).map(String);
  }
  if (typeof parsed.selected_option_id === "string") {
    return [parsed.selected_option_id];
  }
  if (typeof parsed.selected_option === "string") {
    return [parsed.selected_option];
  }
  return [];
}

function getBlankAnswer(answerData: unknown, indexKey: string | number): string {
  const parsed = parseAnswerData(answerData);
  if (!parsed) return "";
  if (parsed.blanks && typeof parsed.blanks === "object") {
    const blanks = parsed.blanks as Record<string, unknown>;
    const val = blanks[String(indexKey)] ?? blanks[Number(indexKey)];
    return typeof val === "string" ? val : "";
  }
  return "";
}

function getMatchingAnswer(answerData: unknown, left: string): string {
  const parsed = parseAnswerData(answerData);
  if (!parsed) return "";
  if (parsed.matches) {
    if (typeof parsed.matches === "object" && !Array.isArray(parsed.matches)) {
      const matches = parsed.matches as Record<string, unknown>;
      const val = matches[left];
      return typeof val === "string" ? val : "";
    }
    if (Array.isArray(parsed.matches)) {
      const matches = parsed.matches as Array<{ left?: string; right?: string }>;
      const found = matches.find((m) => m && m.left === left);
      return found?.right || "";
    }
  }
  return "";
}

interface ExamResultViewProps {
  examId: string;
}

export function ExamResultView({ examId }: ExamResultViewProps) {
  const router = useRouter();
  const { result, isLoading, isError } = useStudentExamResult(examId);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white text-black font-mono">
        <div className="flex items-center gap-4 border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <Loader2 className="w-8 h-8 animate-spin text-black" />
          <span className="text-xl font-bold uppercase tracking-widest">Đang tải kết quả...</span>
        </div>
      </div>
    );
  }

  if (isError || !result) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-white text-black font-mono space-y-6 p-4">
        <p className="text-xl font-bold uppercase tracking-widest border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] text-center">
          Không tìm thấy kết quả bài thi
        </p>
        <button
          onClick={() => router.push("/student/home")}
          className="border-4 border-black bg-black text-white px-8 py-3 uppercase font-bold hover:bg-white hover:text-black transition-all shadow-[8px_8px_0_0_rgba(0,0,0,1)]"
        >
          Quay lại trang chủ
        </button>
      </div>
    );
  }

  const score = result.total_score ?? 0;
  const maxScore = result.max_score ?? 0;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toString().padStart(2, "0")}s`;
  };

  const chartData = [
    { name: "Đúng", count: result.correct_count },
    { name: "Sai", count: result.incorrect_count }
  ];

  return (
    <div className="min-h-screen bg-white text-black font-mono p-4 md:p-8">
      <div className="max-w-4xl mx-auto space-y-8">

        {/* Top Header Card */}
        <div className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <button
              onClick={() => router.push("/student/home")}
              className="flex items-center gap-2 border-2 border-black px-4 py-2 hover:bg-black hover:text-white transition-all font-bold uppercase shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
            >
              <ArrowLeft size={16} /> Quay lại trang chủ
            </button>

            <button
              onClick={() => router.push("/student/home")}
              className="flex items-center gap-2 border-2 border-black px-4 py-2 hover:bg-black hover:text-white transition-all font-bold uppercase shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
            >
              Danh sách bài thi
            </button>
          </div>

          <div className="border-b-4 border-black pb-4">
            <h1 className="text-2xl md:text-3xl font-bold uppercase tracking-widest">
              KẾT QUẢ: {result.title}
            </h1>
          </div>

          {/* Stats Breakdown Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="border-2 border-black p-4 flex flex-col items-center justify-center bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
              <span className="text-xs md:text-sm font-bold uppercase tracking-wider mb-1">Điểm số</span>
              <span data-testid="total-score" className="text-xl md:text-2xl font-bold">
                {score} / {maxScore}
              </span>
            </div>
            <div className="border-2 border-black p-4 flex flex-col items-center justify-center bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
              <span className="text-xs md:text-sm font-bold uppercase tracking-wider mb-1">Thời gian</span>
              <span className="text-xl md:text-2xl font-bold">{formatTime(result.time_taken_seconds || 0)}</span>
            </div>
            <div className="border-2 border-black p-4 flex flex-col items-center justify-center bg-black text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
              <span className="text-xs md:text-sm font-bold uppercase tracking-wider mb-1">Số câu đúng</span>
              <span className="text-xl md:text-2xl font-bold">{result.correct_count}</span>
            </div>
            <div className="border-2 border-black p-4 flex flex-col items-center justify-center bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
              <span className="text-xs md:text-sm font-bold uppercase tracking-wider mb-1">Số câu sai</span>
              <span className="text-xl md:text-2xl font-bold">{result.incorrect_count}</span>
            </div>
          </div>
        </div>

        {/* Summary Chart */}
        <div className="border-4 border-black bg-white p-6 shadow-[8px_8px_0_0_rgba(0,0,0,1)] space-y-4">
          <h2 className="text-xl font-bold uppercase tracking-widest text-black border-b-4 border-black pb-2">
            Biểu đồ tổng quan
          </h2>
          <div className="h-64 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="0" stroke="#000000" vertical={false} />
                <XAxis
                  dataKey="name"
                  stroke="#000000"
                  tick={{ fill: "#000000", fontSize: 12, fontFamily: "monospace" }}
                  axisLine={{ stroke: "#000000", strokeWidth: 2 }}
                  tickLine={{ stroke: "#000000", strokeWidth: 2 }}
                />
                <YAxis
                  stroke="#000000"
                  tick={{ fill: "#000000", fontSize: 12, fontFamily: "monospace" }}
                  axisLine={{ stroke: "#000000", strokeWidth: 2 }}
                  tickLine={{ stroke: "#000000", strokeWidth: 2 }}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "4px solid #000000",
                    borderRadius: 0,
                    color: "#000000",
                    fontFamily: "monospace",
                    boxShadow: "4px 4px 0 0 rgba(0,0,0,1)"
                  }}
                  itemStyle={{ color: "#000000", fontWeight: "bold" }}
                  cursor={{ fill: "#f0f0f0" }}
                />
                <Bar
                  dataKey="count"
                  fill="#000000"
                  stroke="#000000"
                  radius={0}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Detailed Question Review List */}
        <div className="space-y-6">
          <h2 className="text-2xl font-bold uppercase tracking-widest border-b-4 border-black pb-2">
            Chi tiết đáp án
          </h2>

          {(result.answers || []).map((ans, idx) => {
            const isCorrect = ans.is_correct;
            const isUnanswered = !ans.answer_data;
            const qType = (ans.question_type || "").toUpperCase();

            return (
              <div
                key={ans.question_id || idx}
                className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] space-y-4"
              >
                <div className="flex flex-wrap justify-between items-start gap-4 pb-4 border-b-4 border-black">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold border-2 border-black px-3 py-1 bg-black text-white">
                      CÂU {idx + 1}
                    </span>
                    <span className="font-bold uppercase tracking-widest text-sm border-2 border-black px-3 py-1 bg-white">
                      {qType.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div className="flex items-center gap-4">
                    <span className="font-bold border-2 border-black px-3 py-1 bg-white text-black text-sm">
                      {ans.points_awarded} / {ans.points} ĐIỂM
                    </span>
                    {isCorrect ? (
                      <span className="flex items-center gap-1 font-bold border-2 border-black px-3 py-1 bg-black text-white text-sm uppercase">
                        <CheckCircle size={16} /> Đúng
                      </span>
                    ) : isUnanswered ? (
                      <span className="flex items-center gap-1 font-bold border-2 border-dashed border-black px-3 py-1 bg-white text-black text-sm uppercase">
                        <XCircle size={16} /> Chưa trả lời
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 font-bold border-2 border-black px-3 py-1 bg-white text-black text-sm uppercase">
                        <XCircle size={16} /> Sai
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-lg font-bold">
                  {ans.content}
                </div>

                {/* Question Type Content Renderer */}
                <div className="space-y-4 pt-2">
                  {(qType === "SINGLE_CHOICE" || qType === "MULTIPLE_CHOICE" || qType === "TRUE_FALSE") ? (
                    <div className="space-y-3">
                      {(ans.options || []).map((opt) => {
                        const selectedIds = getSelectedOptionIds(ans.answer_data);
                        const isSelected = selectedIds.includes(opt.id);
                        const isOptCorrect = opt.is_correct;

                        return (
                          <div
                            key={opt.id}
                            className={`p-4 border-2 border-black flex flex-wrap items-center justify-between gap-3 ${
                              isSelected ? "bg-black text-white" : "bg-white text-black"
                            }`}
                          >
                            <div className="flex items-center gap-3 flex-1 min-w-[200px]">
                              <div
                                className={`w-5 h-5 border-2 shrink-0 ${
                                  isSelected ? "border-white bg-white" : "border-black bg-white"
                                }`}
                              />
                              <span className="font-medium text-base">{opt.content}</span>
                            </div>

                            <div className="flex items-center gap-2">
                              {isSelected && (
                                <span className={`text-xs uppercase font-bold border-2 px-2 py-0.5 ${
                                  isSelected ? "border-white text-white" : "border-black text-black"
                                }`}>
                                  Lựa chọn của bạn
                                </span>
                              )}
                              {isOptCorrect && (
                                <span className={`text-xs uppercase font-bold border-2 px-2 py-0.5 ${
                                  isSelected ? "border-white text-white bg-black" : "border-black text-black bg-white"
                                }`}>
                                  Đáp án đúng
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : qType === "FILL_IN_BLANK" || qType === "SHORT_ANSWER" ? (
                    <div className="space-y-3">
                      {(() => {
                        const blanksList = (ans.metadata_json?.blanks as BlankAnswer[] | undefined) || [];
                        const blankCount = blanksList.length > 0 ? blanksList.length : (ans.content.match(/\[BLANK\]/g) || [1]).length;

                        return Array.from({ length: blankCount }).map((_, i) => {
                          const blankMeta = blanksList[i];
                          const blankIdx = blankMeta?.blank_index ?? i;
                          const studentAns = getBlankAnswer(ans.answer_data, blankIdx);
                          const acceptable = blankMeta?.acceptable_answers || [];

                          return (
                            <div key={i} className="flex flex-col gap-2 border-2 border-black p-4 bg-white">
                              <span className="font-bold uppercase tracking-widest text-xs border-b-2 border-black pb-1">
                                Ô trống #{blankIdx + 1}
                              </span>
                              <div className="flex flex-wrap gap-2 items-center text-sm">
                                <span className="font-bold uppercase">Lựa chọn của bạn:</span>
                                <span className="border-2 border-black px-3 py-1 font-bold bg-white">
                                  {studentAns || <span className="italic text-black">Chưa trả lời</span>}
                                </span>
                              </div>
                              {acceptable.length > 0 && (
                                <div className="flex flex-wrap gap-2 items-center text-sm">
                                  <span className="font-bold uppercase">Đáp án đúng:</span>
                                  <span className="border-2 border-dashed border-black px-3 py-1 font-bold bg-white">
                                    {acceptable.join(" / ")}
                                  </span>
                                </div>
                              )}
                            </div>
                          );
                        });
                      })()}
                    </div>
                  ) : qType === "MATCHING" ? (
                    <div className="pt-2">
                      {(() => {
                        const pairs = (ans.metadata_json?.pairs as MatchPair[] | undefined) || [];

                        // Parse student matches từ answer_data thành MatchPair[]
                        const studentMatches: MatchPair[] = pairs
                          .map((pair) => {
                            const right = getMatchingAnswer(ans.answer_data, pair.left);
                            return right ? { left: pair.left, right } : null;
                          })
                          .filter(Boolean) as MatchPair[];

                        return (
                          <BrutalistMatchingUI
                            pairs={pairs}
                            currentMatches={studentMatches}
                            onChange={() => {}}
                            readOnly={true}
                            correctMatches={pairs}
                          />
                        );
                      })()}
                    </div>
                  ) : (
                    <div className="p-4 border-2 border-black bg-white italic">
                      Định dạng câu hỏi không xác định.
                    </div>
                  )}
                </div>

              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
}
