"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useStudyCards, submitCardReview } from "@/hooks/useFlashcards";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { logBackendError } from "@/lib/errors";

export default function StudyDeckPage({ params }: { params: Promise<{ id: string; deck_id: string }> }) {
  const resolvedParams = use(params);
  const { id, deck_id } = resolvedParams;
  const router = useRouter();

  const { cards, isLoading, isError } = useStudyCards(deck_id);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isError) {
    return (
      <div className="p-8 font-mono">
        <p role="alert" className="text-xl font-bold uppercase border-4 border-dashed border-black p-4">ĐÃ XẢY RA LỖI KHI TẢI THẺ.</p>
        <Button onClick={() => router.push(`/student/topics/${id}`)} className="mt-4 border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)]">QUAY LẠI</Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-8 font-mono flex items-center justify-center min-h-[60vh]">
        <p className="text-2xl font-black uppercase tracking-widest animate-pulse">ĐANG TẢI THẺ...</p>
      </div>
    );
  }

  if (!cards || cards.length === 0 || currentIndex >= cards.length) {
    return (
      <div className="p-8 font-mono flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter">XIN CHÚC MỪNG!</h1>
        <p className="text-xl md:text-2xl font-bold uppercase border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          BẠN ĐÃ ÔN TẬP XONG TẤT CẢ THẺ HÔM NAY.
        </p>
        <Button
          onClick={() => router.push(`/student/topics/${id}`)}
          className="text-lg py-6 px-10 border-4 border-black bg-black text-white hover:bg-white hover:text-black font-black uppercase shadow-[6px_6px_0_0_rgba(0,0,0,1)] hover:translate-x-[4px] hover:translate-y-[4px] hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] transition-all rounded-none"
        >
          QUAY LẠI CHỦ ĐỀ
        </Button>
      </div>
    );
  }

  const currentCard = cards[currentIndex];

  const handleReview = async (rating: "AGAIN" | "HARD" | "GOOD" | "EASY") => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await submitCardReview(currentCard.id, { rating });
      setIsFlipped(false);
      setCurrentIndex((prev) => prev + 1);
    } catch (error) {
      logBackendError("Flashcard review submit failed", error);
      toast.add({ title: "Thông báo", description: "Đã xảy ra lỗi khi gửi đánh giá. Vui lòng thử lại.", type: "info" });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-4 md:p-8 font-mono max-w-4xl mx-auto min-h-[80vh] flex flex-col items-center">
      <div className="w-full flex justify-between items-center mb-8">
        <Button
          onClick={() => router.push(`/student/topics/${id}`)}
          variant="outline"
          className="border-4 border-black font-bold rounded-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
        >
          &larr; THOÁT
        </Button>
        <div className="font-bold border-4 border-black px-4 py-2 bg-white shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
          THẺ: {currentIndex + 1} / {cards.length}
        </div>
      </div>

      <div className="w-full aspect-[4/3] md:aspect-[16/9] [perspective:1000px] mb-12">
        <button
          type="button"
          aria-label={isFlipped ? "Card answer revealed" : "Reveal card answer"}
          aria-pressed={isFlipped}
          className={`relative block w-full h-full transition-transform duration-700 [transform-style:preserve-3d] cursor-pointer focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-black ${
            isFlipped ? "[transform:rotateY(180deg)]" : ""
          }`}
          onClick={() => !isFlipped && setIsFlipped(true)}
        >
          {/* Front */}
          <div className="absolute inset-0 [backface-visibility:hidden] border-8 border-black bg-white shadow-[12px_12px_0_0_rgba(0,0,0,1)] flex flex-col items-center justify-center p-8 md:p-12 text-center">
            <span className="absolute top-4 left-4 font-black uppercase text-xl border-b-4 border-black pb-1">MẶT TRƯỚC</span>
            <p className="text-2xl md:text-5xl font-black uppercase break-words">{currentCard.front_content}</p>
            {!isFlipped && (
              <p className="absolute bottom-6 font-bold uppercase animate-pulse border-4 border-black px-4 py-2 bg-black text-white">
                CHẠM ĐỂ LẬT &rarr;
              </p>
            )}
          </div>

          {/* Back */}
          <div className="absolute inset-0 [backface-visibility:hidden] [transform:rotateY(180deg)] border-8 border-black bg-white shadow-[12px_12px_0_0_rgba(0,0,0,1)] flex flex-col items-center justify-center p-8 md:p-12 text-center">
            <span className="absolute top-4 left-4 font-black uppercase text-xl border-b-4 border-black pb-1">MẶT SAU</span>
            <p className="text-xl md:text-4xl font-bold break-words">{currentCard.back_content}</p>
          </div>
        </button>
      </div>

      {isFlipped && (
        <div className="w-full flex flex-col gap-4 animate-in fade-in duration-500">
          <p className="font-black text-xl text-center uppercase mb-2">ĐÁNH GIÁ ĐỘ KHÓ:</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full">
            <Button
              onClick={() => handleReview("AGAIN")}
              disabled={isSubmitting}
              className="py-8 text-lg border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all font-black bg-white text-black hover:bg-black hover:text-white"
            >
              [LÀM LẠI]
            </Button>
            <Button
              onClick={() => handleReview("HARD")}
              disabled={isSubmitting}
              className="py-8 text-lg border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all font-black bg-white text-black hover:bg-black hover:text-white"
            >
              [KHÓ]
            </Button>
            <Button
              onClick={() => handleReview("GOOD")}
              disabled={isSubmitting}
              className="py-8 text-lg border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all font-black bg-white text-black hover:bg-black hover:text-white"
            >
              [TỐT]
            </Button>
            <Button
              onClick={() => handleReview("EASY")}
              disabled={isSubmitting}
              className="py-8 text-lg border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all font-black bg-white text-black hover:bg-black hover:text-white"
            >
              [DỄ QUÁ]
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
