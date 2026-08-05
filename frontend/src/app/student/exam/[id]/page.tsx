"use client";

import React, { useState, useEffect, use } from 'react';
import { useTakeExam, submitExam } from '@/hooks/useStudentExams';
import { Loader2, Clock, CheckCircle, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import BrutalistMatchingUI from '@/components/features/student/BrutalistMatchingUI';
import { toast } from "@/components/ui/toast";
import { useConfirm } from "@/hooks/useConfirm";
// Utility for answers
type MatchPair = { left: string; right: string };

// Utility for answers

export default function StudentExamTakingPage({ params }: { params: Promise<{ id: string }> }) {
  const unwrappedParams = use(params);
  const router = useRouter();
  const { exam, isLoading, isError } = useTakeExam(unwrappedParams.id);
  
  const [answers, setAnswers] = useState<Record<string, Record<string, unknown>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { confirm, ConfirmDialog } = useConfirm();
  
  // Timer State
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  useEffect(() => {
    if (exam && timeLeft === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTimeLeft(exam.duration_minutes * 60);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exam]);

  useEffect(() => {
    if (timeLeft === null || isSubmitting) return;
    
    if (timeLeft <= 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsSubmitting(true);
      submitExam(unwrappedParams.id, { answers: Object.values(answers) })
        .then(() => router.push(`/student/exam/${unwrappedParams.id}/result`))
        .catch((err: unknown) => {
          console.error("Auto submit error:", err);
          setIsSubmitting(false);
        });
      return;
    }
    
    const timerId = setInterval(() => {
      setTimeLeft((prev) => (prev ? prev - 1 : 0));
    }, 1000);
    
    return () => clearInterval(timerId);
  }, [timeLeft, isSubmitting, answers, router, unwrappedParams.id]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleSingleChoiceChange = (qId: string, optionId: string) => {
    setAnswers((prev) => ({
      ...prev,
      [qId]: {
        question_id: qId,
        selected_option_id: optionId
      }
    }));
  };

  const handleMultipleChoiceChange = (qId: string, optionId: string, isChecked: boolean) => {
    setAnswers((prev) => {
      const existing = prev[qId] || {};
      const answerData = (existing.answer_data as Record<string, unknown>) || { selected_option_ids: [] };
      let newIds = (answerData.selected_option_ids as string[]) || [];
      
      if (isChecked) {
        if (!newIds.includes(optionId)) newIds = [...newIds, optionId];
      } else {
        newIds = newIds.filter((id: string) => id !== optionId);
      }
      
      return {
        ...prev,
        [qId]: {
          ...existing,
          question_id: qId,
          answer_data: {
            ...answerData,
            selected_option_ids: newIds
          }
        }
      };
    });
  };

  const handleFillInBlankChange = (qId: string, blankIndex: number, value: string) => {
    setAnswers((prev) => {
      const existing = prev[qId] || {};
      const answerData = (existing.answer_data as Record<string, unknown>) || { blanks: {} };
      const blanks = (answerData.blanks as Record<number, string>) || {};
      
      return {
        ...prev,
        [qId]: {
          ...existing,
          question_id: qId,
          answer_data: {
            ...answerData,
            blanks: {
              ...blanks,
              [blankIndex]: value
            }
          }
        }
      };
    });
  };


  const handleMatchingArrayChange = (qId: string, newMatches: MatchPair[]) => {
    setAnswers((prev) => {
      const existing = prev[qId] || {};
      const answerData = (existing.answer_data as Record<string, unknown>) || { matches: [] };
      return {
        ...prev,
        [qId]: {
          ...existing,
          question_id: qId,
          answer_data: {
            ...answerData,
            matches: newMatches
          }
        }
      };
    });
  };


  const handleSubmit = async () => {
    if (isSubmitting) return;
    
    if (timeLeft !== null && timeLeft > 0) {
      if (!await confirm("Bạn có chắc chắn muốn nộp bài?")) return;
    }
    
    setIsSubmitting(true);
    try {
      const payload = {
        answers: Object.values(answers)
      };
      await submitExam(unwrappedParams.id, payload);
      router.push(`/student/exam/${unwrappedParams.id}/result`);
    } catch (error: unknown) {
      console.error("Submit error:", error);
      const err = error as { response?: { data?: { detail?: string } } };
      toast.add({ title: "Thông báo", description: err?.response?.data?.detail || "Đã xảy ra lỗi khi nộp bài", type: "info" });
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen bg-white text-black">
        <Loader2 className="animate-spin" size={64} />
      </div>
    );
  }

  if (isError || !exam) {
    return (
      <div className="flex flex-col justify-center items-center h-screen bg-white text-black">
        <h1 className="text-3xl font-bold uppercase">Lỗi tải đề thi</h1>
        <p className="mt-4 font-mono">Đề thi không tồn tại hoặc bạn đã nộp bài.</p>
        <button 
          onClick={() => router.push('/student/home')}
          className="mt-8 px-6 py-2 border-4 border-black bg-black text-white font-bold uppercase hover:bg-white hover:text-black transition-colors"
        >
          Về trang chủ
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white text-black pb-32">
      <div className="sticky top-0 z-50 bg-white border-b-4 border-black shadow-[0_4px_0_0_rgba(0,0,0,1)] p-4 lg:p-6 flex justify-between items-center gap-4 flex-wrap">
        <div className="flex items-center gap-4 lg:gap-6">
          <button 
            onClick={() => router.push('/student/topics')} 
            className="flex px-3 py-2 lg:px-4 lg:py-2 border-4 border-black bg-white hover:bg-black hover:text-white font-bold uppercase transition-colors shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] items-center gap-2"
          >
            <LogOut className="w-5 h-5" />
            <span className="hidden md:inline">THOÁT BÀI THI</span>
          </button>
          <div>
            <h1 className="text-xl lg:text-3xl font-bold uppercase tracking-widest">{exam.title}</h1>
            <p className="text-sm font-mono mt-1 font-bold">Tổng điểm: {exam.questions?.reduce((sum, q) => sum + (Number(q.points) || 0), 0) || 0}</p>
          </div>
        </div>
        <div className={`flex items-center gap-2 lg:gap-3 border-4 border-black px-4 py-2 lg:px-6 lg:py-3 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] bg-white ${timeLeft !== null && timeLeft < 60 ? 'animate-pulse text-red-600 border-red-600' : ''}`}>
          <Clock className="w-6 h-6" />
          <span className="text-2xl font-mono font-bold tracking-widest">
            {timeLeft !== null ? formatTime(timeLeft) : "--:--"}
          </span>
        </div>
      </div>

      <main className="max-w-4xl mx-auto p-4 lg:p-8 mt-8 space-y-12">
        {exam.questions.map((q, idx) => (
          <div key={q.id} data-testid={`question-container-${idx}`} className="border-4 border-black p-6 lg:p-10 bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative">
            <div className="absolute -top-4 -left-4 bg-black text-white px-4 py-2 border-4 border-white font-bold font-mono text-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              CÂU {idx + 1}
            </div>
            
            <div className="mt-4 flex gap-3 mb-6 border-b-4 border-black pb-4">
              <span className="border-2 border-black px-3 py-1 text-sm font-mono font-bold uppercase">
                {q.question_type?.replace(/_/g, ' ')}
              </span>
              <span className="border-2 border-black px-3 py-1 text-sm font-mono font-bold uppercase bg-gray-100">
                {q.points} Điểm
              </span>
            </div>

            {q.question_type === "FILL_IN_BLANK" ? (
              <div className="text-xl leading-loose font-mono font-medium">
                {q.content.split("[BLANK]").map((part, index, arr) => (
                  <React.Fragment key={index}>
                    {part}
                    {index < arr.length - 1 && (
                      <input
                        type="text"
                        data-testid={`blank-${q.id}-${index}`}
                        value={((answers[q.id]?.answer_data as Record<string, unknown>)?.blanks as Record<number, string>)?.[index] || ""}
                        onChange={(e) => handleFillInBlankChange(q.id, index, e.target.value)}
                        className="mx-2 px-3 py-1 border-b-4 border-black border-dashed bg-gray-100 focus:outline-none focus:border-solid focus:bg-yellow-100 w-32 md:w-48 text-center font-bold transition-all"
                        placeholder={`(#${index + 1})`}
                      />
                    )}
                  </React.Fragment>
                ))}
              </div>
            ) : (
              <h3 className="text-2xl font-bold whitespace-pre-wrap leading-relaxed">{q.content}</h3>
            )}

            <div className="mt-8 space-y-4">
              {(q.question_type === "SINGLE_CHOICE" || q.question_type === "true_false" || q.question_type === "single_choice") && (
                <div className="space-y-4">
                  {q.options?.map((opt, i) => (
                    <label 
                      key={opt.id || i} 
                      className={`flex items-center gap-4 p-4 border-4 border-black cursor-pointer transition-all ${
                        answers[q.id]?.selected_option_id === opt.id 
                          ? 'bg-black text-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] translate-x-[-2px] translate-y-[-2px]' 
                          : 'bg-white hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="radio"
                        data-testid={`option-${q.id}-${opt.id}`}
                        name={`q_${q.id}`}
                        checked={answers[q.id]?.selected_option_id === opt.id}
                        onChange={() => handleSingleChoiceChange(q.id, opt.id)}
                        className="w-6 h-6 border-4 border-black accent-white"
                      />
                      <span className="font-mono text-xl font-bold w-8">{String.fromCharCode(65 + i)}.</span>
                      <span className="text-lg font-medium flex-1">{opt.content}</span>
                    </label>
                  ))}
                </div>
              )}

              {(q.question_type === "MULTIPLE_CHOICE" || q.question_type === "multiple_choice") && (
                <div className="space-y-4">
                  {q.options?.map((opt, i) => {
                    const isChecked = ((answers[q.id]?.answer_data as Record<string, unknown>)?.selected_option_ids as string[])?.includes(opt.id);
                    return (
                      <label 
                        key={opt.id || i} 
                        className={`flex items-center gap-4 p-4 border-4 border-black cursor-pointer transition-all ${
                          isChecked 
                            ? 'bg-black text-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] translate-x-[-2px] translate-y-[-2px]' 
                            : 'bg-white hover:bg-gray-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          data-testid={`option-${q.id}-${opt.id}`}
                          checked={isChecked || false}
                          onChange={(e) => handleMultipleChoiceChange(q.id, opt.id, e.target.checked)}
                          className="w-6 h-6 border-4 border-black accent-white"
                        />
                        <span className="font-mono text-xl font-bold w-8">{String.fromCharCode(65 + i)}.</span>
                        <span className="text-lg font-medium flex-1">{opt.content}</span>
                      </label>
                    );
                  })}
                </div>
              )}

              {q.question_type === "MATCHING" && (
                <div className="w-full">
                  <BrutalistMatchingUI
                    pairs={(q.metadata_json?.pairs || []) as MatchPair[]}
                    currentMatches={((answers[q.id]?.answer_data as Record<string, unknown>)?.matches as MatchPair[]) || []}
                    onChange={(newMatches) => handleMatchingArrayChange(q.id, newMatches)}
                  />
                </div>
              )}
            </div>
          </div>
        ))}
        
        <div className="pt-12 pb-12 flex justify-center">
          <button
            onClick={handleSubmit}
            data-testid="submit-exam-button"
            disabled={isSubmitting}
            className="group flex items-center gap-4 px-12 py-6 border-4 border-black bg-black text-white hover:bg-white hover:text-black transition-all shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[12px] hover:translate-y-[12px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <Loader2 className="animate-spin w-10 h-10" />
            ) : (
              <CheckCircle className="w-10 h-10" />
            )}
            <span className="text-3xl font-bold uppercase tracking-widest font-mono">
              {isSubmitting ? "Đang Nộp Bài..." : "Nộp Bài Ngay"}
            </span>
          </button>
        </div>
      </main>
      <ConfirmDialog />
    </div>
  );
}
