"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { useTakeExam } from "@/hooks/useStudentExams";
import { submitExam } from "@/services/apiService";
import { toast } from "@/components/ui/toast";

export default function ExamEngine({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const { exam, isLoading, isError } = useTakeExam(resolvedParams.id);
  const router = useRouter();

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timeLeft, setTimeLeft] = useState(0);
  const [timeInitialized, setTimeInitialized] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  if (exam && !timeInitialized) {
    setTimeLeft(exam.duration_minutes * 60);
    setTimeInitialized(true);
  }

  const handleSubmit = async () => {
    if (isSubmitting || !exam) return;
    setIsSubmitting(true);

    try {
      const payload = {
        answers: Object.entries(answers).map(([question_id, selected_option_id]) => ({
          question_id,
          selected_option_id,
        })),
      };
      
      await submitExam(exam.id, payload);
      
      toast.add({
        title: "Nộp bài thành công",
        description: "Bài làm của bạn đã được ghi nhận.",
        type: "success",
      });
      
      router.push(`/student/exams/${exam.id}/result`);
    } catch {
      toast.add({
        title: "Lỗi nộp bài",
        description: "Đã xảy ra lỗi, vui lòng thử lại.",
        type: "error",
      });
      setIsSubmitting(false);
    }
  };

  const handleAutoSubmit = async () => {
    toast.add({
      title: "Hết giờ",
      description: "Hệ thống đang tự động nộp bài...",
      type: "info",
    });
    await handleSubmit();
  };

  useEffect(() => {
    if (!timeInitialized) return;
    if (timeLeft <= 0) {
      if (timeLeft === 0 && !isSubmitting && exam) {
        setTimeout(() => handleAutoSubmit(), 0);
      }
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft, isSubmitting, exam, timeInitialized]);

  if (isError) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="bg-surface rounded-[32px] border-2 border-dashed border-outline-variant p-12 text-center h-full flex flex-col items-center justify-center">
          <span className="material-symbols-outlined text-6xl text-error mb-4">error</span>
          <p className="text-lg font-medium text-on-surface-variant">Lỗi tải đề thi</p>
          <p className="text-sm text-outline mb-6">Bạn đã nộp bài này hoặc không có quyền truy cập.</p>
          <button className="bg-primary text-on-primary px-6 py-2 rounded-full font-label-bold" onClick={() => router.push("/student/dashboard")}>
            Quay lại
          </button>
        </div>
      </div>
    );
  }

  if (isLoading || !exam || !timeInitialized) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <span className="material-symbols-outlined animate-spin text-primary text-4xl">sync</span>
      </div>
    );
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const isLowTime = timeLeft <= 300; // less than 5 mins
  const currentQuestion = exam.questions[currentIndex];
  const progressPercent = Math.round((Object.keys(answers).length / exam.questions.length) * 100);

  return (
    <>
      {/* Fixed Top Bar */}
      <header className="fixed top-0 left-0 w-full bg-surface shadow-[0px_4px_20px_rgba(0,102,138,0.15)] z-50">
        <div className="max-w-[1200px] mx-auto px-container-padding-desktop py-4 flex justify-between items-center">
          <div className="flex items-center gap-4 hidden sm:flex">
            <span className="material-symbols-outlined text-primary text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>rocket_launch</span>
            <h1 className="font-headline-md text-headline-md text-primary tracking-tight line-clamp-1 max-w-[200px] md:max-w-md">{exam.title}</h1>
          </div>
          <div className="flex items-center gap-4 sm:gap-8 w-full sm:w-auto justify-between sm:justify-end">
            <div className="bg-primary-container/30 px-6 py-2 rounded-full border-2 border-primary-container text-primary font-label-bold text-label-bold">
              Câu {currentIndex + 1} / {exam.questions.length}
            </div>
            <div className={`flex items-center gap-2 px-6 py-2 rounded-full border-2 ${isLowTime ? 'bg-error-container border-error text-error' : 'bg-tertiary-fixed-dim/20 border-tertiary-fixed-dim text-tertiary'}`}>
              <span className="material-symbols-outlined text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>schedule</span>
              <span className={`font-headline-md text-headline-md ${isLowTime ? 'animate-pulse' : ''}`}>{formatTime(timeLeft)}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter mt-8 pb-32">
        {/* Left Column: Question & Answers */}
        <div className="lg:col-span-8 flex flex-col gap-stack-gap-lg">
          {/* Question Card */}
          <div className="bg-surface rounded-xl border-2 border-surface-variant shadow-level-1 p-8 flex flex-col items-center text-center">
            <h2 className="font-headline-lg text-headline-lg text-primary mb-4 whitespace-pre-wrap">{currentQuestion.content}</h2>
            <p className="text-on-surface-variant font-label-sm">Điểm: {currentQuestion.points}</p>
          </div>

          {/* Answer Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-stack-gap-md">
            {currentQuestion.options.map((opt, index) => {
              const isSelected = answers[currentQuestion.id] === opt.id;
              const letter = String.fromCharCode(65 + index);
              
              return (
                <button
                  key={opt.id}
                  onClick={() => setAnswers({ ...answers, [currentQuestion.id]: opt.id })}
                  className={`rounded-xl border-2 shadow-level-1 p-6 flex items-center gap-4 transition-all text-left relative overflow-hidden group ${
                    isSelected 
                      ? 'bg-primary-fixed/20 border-primary text-primary' 
                      : 'bg-surface border-surface-variant hover:border-primary hover:bg-primary-fixed/20'
                  }`}
                >
                  <div className={`w-12 h-12 shrink-0 rounded-full flex items-center justify-center font-headline-md text-headline-md transition-colors ${
                    isSelected 
                      ? 'bg-primary text-on-primary shadow-inner' 
                      : 'bg-surface-container-high text-on-surface-variant group-hover:bg-primary group-hover:text-on-primary'
                  }`}>
                    {letter}
                  </div>
                  <span className={`font-body-lg text-body-lg flex-grow ${isSelected ? 'font-bold' : ''}`}>
                    {opt.content}
                  </span>
                  {isSelected && (
                    <span className="material-symbols-outlined absolute right-6 text-3xl opacity-50" style={{ fontVariationSettings: "'FILL' 1" }}>stars</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Rocket Progress Bar */}
          <div className="mt-4 bg-surface rounded-xl border-2 border-surface-variant shadow-level-1 p-6">
            <div className="flex justify-between items-center mb-4">
              <span className="font-label-bold text-label-bold text-primary">Hành trình Khám phá</span>
              <span className="font-label-bold text-label-bold text-on-surface-variant">{progressPercent}%</span>
            </div>
            <div className="relative h-6 bg-surface-container-highest rounded-full progress-well overflow-visible flex items-center">
              <div className="absolute h-full bg-secondary rounded-full w-0" style={{ width: `${progressPercent}%`, transition: 'width 0.5s ease-in-out', boxShadow: 'inset 0px 4px 0px rgba(255, 255, 255, 0.3)' }}></div>
              <div className="absolute z-10 w-12 h-12 bg-surface rounded-full shadow-md flex items-center justify-center border-2 border-secondary" style={{ left: `${Math.max(0, progressPercent - 5)}%`, transition: 'left 0.5s ease-in-out' }}>
                <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>rocket</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Question Map */}
        <div className="lg:col-span-4">
          <div className="bg-surface rounded-xl border-2 border-surface-variant shadow-level-1 p-6 lg:sticky top-32">
            <h3 className="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-tertiary" style={{ fontVariationSettings: "'FILL' 1" }}>map</span>
              Bản đồ Sao
            </h3>
            <div className="grid grid-cols-5 gap-3">
              {exam.questions.map((q, idx) => {
                const isAnswered = !!answers[q.id];
                const isCurrent = idx === currentIndex;
                
                if (isCurrent) {
                  return (
                    <button 
                      key={q.id}
                      className="aspect-square rounded-lg bg-primary text-on-primary border-2 border-primary flex items-center justify-center relative overflow-hidden ring-4 ring-primary-fixed/50"
                    >
                      <span className="font-headline-md text-headline-md">{idx + 1}</span>
                      <div className="absolute inset-0" style={{ boxShadow: 'inset 0px 4px 0px rgba(255, 255, 255, 0.3)' }}></div>
                    </button>
                  );
                }
                
                if (isAnswered) {
                  return (
                    <button 
                      key={q.id}
                      onClick={() => setCurrentIndex(idx)}
                      className="aspect-square rounded-lg bg-surface-container border-2 border-surface-variant flex items-center justify-center text-on-surface-variant hover:bg-surface-variant transition-colors relative overflow-hidden group"
                    >
                      <span className="font-label-bold text-label-bold group-hover:hidden">{idx + 1}</span>
                      <span className="material-symbols-outlined text-primary hidden group-hover:block" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                      <div className="absolute inset-0 bg-primary/10"></div>
                    </button>
                  );
                }
                
                return (
                  <button 
                    key={q.id}
                    onClick={() => setCurrentIndex(idx)}
                    className="aspect-square rounded-lg bg-surface border-2 border-outline-variant flex items-center justify-center text-outline hover:border-primary transition-colors"
                  >
                    <span className="font-label-bold text-label-bold">{idx + 1}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Action Bar */}
      <footer className="fixed bottom-0 left-0 w-full bg-surface shadow-[0px_-4px_20px_rgba(0,102,138,0.1)] z-40">
        <div className="max-w-[1200px] mx-auto px-container-padding-mobile md:px-container-padding-desktop py-4 flex justify-between items-center">
          <button 
            onClick={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
            className="h-14 px-4 sm:px-8 rounded-full border-2 border-surface-variant bg-surface text-on-surface-variant font-label-bold text-label-bold flex items-center gap-2 hover:bg-surface-variant transition-colors disabled:opacity-50"
          >
            <span className="material-symbols-outlined">arrow_back</span>
            <span className="hidden sm:inline">Quay lại</span>
          </button>
          
          {currentIndex === exam.questions.length - 1 ? (
            <button 
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="h-14 px-6 sm:px-10 rounded-full bg-success text-on-primary font-headline-md text-headline-md flex items-center gap-3 relative overflow-hidden group shadow-[0px_8px_30px_rgba(16,185,129,0.25)] hover:-translate-y-1 transition-all disabled:opacity-50"
            >
              {isSubmitting && <span className="material-symbols-outlined animate-spin">sync</span>}
              Nộp Bài
              <span className="material-symbols-outlined group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" style={{ fontVariationSettings: "'FILL' 1" }}>task_alt</span>
            </button>
          ) : (
            <button 
              onClick={() => setCurrentIndex(prev => Math.min(exam.questions.length - 1, prev + 1))}
              className="h-14 px-6 sm:px-10 rounded-full bg-primary text-on-primary font-headline-md text-headline-md flex items-center gap-3 relative overflow-hidden group shadow-[0px_8px_30px_rgba(0,102,138,0.25)] hover:-translate-y-1 transition-all"
            >
              Tiếp theo
              <span className="material-symbols-outlined group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" style={{ fontVariationSettings: "'FILL' 1" }}>rocket_launch</span>
            </button>
          )}
        </div>
      </footer>
    </>
  );
}
