"use client";

import React, { use, useCallback } from "react";
import { useSubmissionGradeOverride } from "@/hooks/useExamHistory";
import { Loader2, ArrowLeft, CheckCircle2, XCircle } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { toast } from "@/components/ui/toast";
import { getBackendErrorMessage, logBackendError } from "@/lib/errors";
import AnswerGradeEditor from "./AnswerGradeEditor";

/**
 * Safe fallback for a refusal that carries no recognised `error_code`. The
 * backend's 404 is deliberately indistinguishable between a missing
 * submission and one owned by somebody else, so the message must not claim
 * which of the two happened.
 */
const SAVE_ERROR_FALLBACK =
  "The score could not be corrected. Reload the submission and try again.";

export default function HistoryDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const unwrappedParams = use(params);

  const handleSaveError = useCallback((error: unknown) => {
    logBackendError("Submission grade override failed", error);
    toast.add({
      title: "Grade correction failed",
      description: getBackendErrorMessage(error, SAVE_ERROR_FALLBACK),
      type: "error",
    });
  }, []);

  const { submission, isLoading, isError, pendingQuestionId, saveGrade } =
    useSubmissionGradeOverride(unwrappedParams.id, handleSaveError);

  const handleSave = useCallback(
    async (questionId: string, pointsAwarded: number, reason: string) => {
      const accepted = await saveGrade(questionId, pointsAwarded, reason);
      // Failures are surfaced by `handleSaveError`; only a correction the
      // server actually stored is announced as a success.
      if (accepted) {
        toast.add({
          title: "Success",
          description:
            "Grade correction saved. The submission total has been recalculated.",
          type: "success",
        });
      }
      return accepted;
    },
    [saveGrade],
  );

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
            <h1 className="text-4xl font-bold tracking-tight uppercase font-mono">Submission Detail</h1>
            <p className="text-black font-mono font-bold mt-2 uppercase border-2 border-black inline-block px-3 py-1 shadow-[2px_2px_0_0_rgba(0,0,0,1)] bg-white">ID: {submission.id}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
            <h3 className="text-lg font-bold uppercase font-mono border-b-2 border-black pb-2 mb-4">Student Information</h3>
            <div className="space-y-4 font-mono text-lg">
              <p className="flex justify-between border-b-2 border-dashed border-black pb-2"><span>NAME:</span> <span className="font-bold uppercase text-right">{submission.student_name}</span></p>
              <p className="flex justify-between border-b-2 border-dashed border-black pb-2"><span>EMAIL:</span> <span className="font-bold uppercase text-right">{submission.student_email}</span></p>
              <p className="flex justify-between items-center"><span>STATUS:</span> <span className="font-bold uppercase border-2 border-black px-3 py-1 bg-black text-white">{submission.status}</span></p>
            </div>
          </div>

          <div className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
            <h3 className="text-lg font-bold uppercase font-mono border-b-2 border-black pb-2 mb-4">Exam Information</h3>
            <div className="space-y-4 font-mono text-lg">
              <p className="flex justify-between border-b-2 border-dashed border-black pb-2"><span>EXAM:</span> <span className="font-bold uppercase text-right">{submission.exam_title}</span></p>
              <p className="flex justify-between border-b-2 border-dashed border-black pb-2 items-center"><span>SCORE:</span> <span className="text-2xl font-bold border-2 border-black px-3 py-1 shadow-[2px_2px_0_0_rgba(0,0,0,1)] bg-white">{submission.total_score}</span></p>
              <p className="flex justify-between"><span>SUBMITTED:</span> <span className="font-bold uppercase text-right">{new Date(submission.start_time || "").toLocaleString('en-US')}</span></p>
            </div>
          </div>
        </div>

        <div className="mt-16">
          <h2 className="text-3xl font-bold font-mono uppercase mb-8 border-b-4 border-black pb-4 inline-block">Question Details</h2>
          <div className="space-y-8">
            {submission.answers && submission.answers.length > 0 ? (
              submission.answers.map((ans, idx) => (
                <div key={ans.question_id} className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
                  <div className="flex flex-col sm:flex-row items-start justify-between mb-6 gap-4">
                    <h4 className="font-bold text-xl font-mono uppercase leading-relaxed"><span className="bg-black text-white px-3 py-1 mr-3 border-2 border-black inline-block mb-2 sm:mb-0">QUESTION {idx + 1}</span> {ans.question_content}</h4>
                    <div className="flex items-center gap-4 shrink-0">
                      <span className="font-bold font-mono text-lg border-2 border-black px-4 py-2 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] uppercase whitespace-nowrap">
                        {ans.points_awarded} POINTS
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
                  
                  <AnswerGradeEditor
                    answer={ans}
                    isSaving={pendingQuestionId === ans.question_id}
                    isLocked={pendingQuestionId !== null}
                    onSave={handleSave}
                  />

                  <div className="mt-6 p-6 border-2 border-black bg-white shadow-inner">
                    <p className="text-lg font-bold font-mono uppercase text-black mb-4 border-b-2 border-black pb-2 inline-block">ANSWER DATA:</p>
                    <pre className="whitespace-pre-wrap font-mono text-base bg-white border-2 border-black p-4 overflow-x-auto shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
                      {JSON.stringify(ans.answer_data, null, 2)}
                    </pre>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-12 border-4 border-black border-dashed text-center text-black font-bold font-mono text-xl uppercase bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
                NO ANSWER DATA AVAILABLE
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
