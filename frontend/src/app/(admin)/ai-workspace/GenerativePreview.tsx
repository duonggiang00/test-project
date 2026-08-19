import React from "react";
import { Loader2 } from "lucide-react";
import GenerationJobReview from "./GenerationJobReview";

interface GenerativePreviewProps {
  toolName: string | null;
  toolArgs: string | Record<string, unknown> | null;
  isStreaming: boolean;
}

const DEFAULT_PUBLISH_TITLES: Record<string, string> = {
  draft_exam: "AI-generated questions",
  draft_flashcards: "AI-generated flashcards",
  draft_topic_brief: "AI-generated topic brief",
};

export default function GenerativePreview({ toolName, toolArgs, isStreaming }: GenerativePreviewProps) {
  if (!toolName) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center bg-white border-4 border-black m-4 shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
        <div className="text-center font-mono opacity-50 text-black">
          <span className="material-symbols-outlined text-6xl mb-4 block">auto_awesome</span>
          <p className="font-bold text-lg uppercase">Generative UI Area</p>
          <p className="text-sm mt-2">Dữ liệu AI sinh ra sẽ được hiển thị và chỉnh sửa tại đây.</p>
        </div>
      </div>
    );
  }

  // Attempt to parse toolArgs (it might be a partial JSON string if streaming, or an object if finished)
  let parsedArgs: Record<string, unknown> | null = null;
  let partialStr = "";
  if (typeof toolArgs === "string") {
    partialStr = toolArgs;
    try {
      parsedArgs = JSON.parse(toolArgs);
    } catch {
      // Still streaming/incomplete JSON
    }
  } else {
    parsedArgs = toolArgs as Record<string, unknown> | null;
  }

  // A generation response identifies the review job its draft was parked in.
  // A chat-driven tool call has no job, so nothing about it is publishable and
  // the panel says so rather than offering an action that would 404.
  const jobId =
    typeof parsedArgs?.job_id === "string" && parsedArgs.job_id
      ? parsedArgs.job_id
      : null;
  const publishTitle =
    typeof parsedArgs?.title === "string" && parsedArgs.title
      ? parsedArgs.title
      : DEFAULT_PUBLISH_TITLES[toolName] ?? null;

  return (
    <div className="flex-1 p-6 bg-white overflow-y-auto">
      <div className="mb-6 pb-2 border-b-4 border-black space-y-3">
        <h3 className="text-xl font-bold font-mono flex items-center gap-2 text-black">
          {toolName === "draft_exam" && "[EXAM] Drafting Exam..."}
          {toolName === "draft_flashcards" && "[CARDS] Drafting Flashcards..."}
          {toolName === "draft_topic_brief" && "[DOC] Drafting Brief..."}
          {isStreaming && <Loader2 className="animate-spin w-5 h-5 ml-2 text-black" />}
        </h3>
        {!isStreaming && (
          <GenerationJobReview jobId={jobId} title={publishTitle} />
        )}
      </div>

      {!parsedArgs ? (
        <div className="font-mono text-sm bg-white p-4 border-4 border-black whitespace-pre-wrap shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
          <div className="animate-pulse flex space-x-2">
             <div className="h-2 bg-black w-1/4"></div>
             <div className="h-2 bg-black w-1/2"></div>
          </div>
          <div className="mt-4 text-xs opacity-50 text-black">Streaming raw data...</div>
          <div className="mt-2 text-xs text-black">{partialStr.slice(-100)}</div>
        </div>
      ) : (
        <div className="space-y-4">
          {toolName === "draft_exam" && (
            <div>
              <h4 className="font-bold text-lg mb-4 font-mono uppercase bg-black text-white p-2">
                {typeof parsedArgs.title === "string" ? parsedArgs.title : "Untitled Exam"}
              </h4>
              <div className="space-y-4">
                {(Array.isArray(parsedArgs.questions) ? parsedArgs.questions : []).map((q: Record<string, unknown>, i: number) => (
                  <div key={i} className="border-4 border-black p-4 shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white text-black">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-bold font-mono">Q{i + 1}. {String(q.content || "")}</span>
                      <div className="flex gap-2">
                        <span className="bg-white border-2 border-black px-2 py-1 text-xs font-mono font-bold uppercase shadow-[2px_2px_0_0_rgba(0,0,0,1)]">{String(q.difficulty || "MEDIUM")}</span>
                        <span className="bg-black text-white border-2 border-black px-2 py-1 text-xs font-mono font-bold uppercase shadow-[2px_2px_0_0_rgba(0,0,0,1)]">{String(q.type || "")}</span>
                      </div>
                    </div>
                    {Array.isArray(q.options) && q.options.length > 0 && (
                      <ul className="mt-2 space-y-2 border-t-2 border-black pt-2">
                        {q.options.map((opt: Record<string, unknown>, j: number) => (
                          <li key={j} className="flex items-center gap-2 font-mono text-sm font-bold">
                            <span className="material-symbols-outlined text-base font-bold">
                              {opt.is_correct ? "check_box" : "check_box_outline_blank"}
                            </span>
                            {String(opt.content || "")}
                          </li>
                        ))}
                      </ul>
                    )}
                    {q.type === "MATCHING" && !!q.metadata_json && !!(q.metadata_json as Record<string, unknown>).pairs && (
                      <div className="mt-2 border-t-2 border-black pt-2">
                        <p className="text-xs font-mono font-bold uppercase mb-2 underline">Các cặp ghép nối:</p>
                        <ul className="space-y-1">
                          {((q.metadata_json as Record<string, unknown>).pairs as Record<string, string>[]).map((pair: Record<string, string>, j: number) => (
                            <li key={j} className="font-mono text-sm font-bold flex gap-2">
                              <span>-</span>
                              <span>{pair.left}</span>
                              <span className="material-symbols-outlined text-sm">arrow_forward</span>
                              <span>{pair.right}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {q.type === "FILL_IN_BLANK" && !!q.metadata_json && !!(q.metadata_json as Record<string, unknown>).blanks && (
                      <div className="mt-2 border-t-2 border-black pt-2">
                        <p className="text-xs font-mono font-bold uppercase mb-2 underline">Các chỗ trống cần điền:</p>
                        <ul className="space-y-1">
                          {((q.metadata_json as Record<string, unknown>).blanks as { blank_index?: number; acceptable_answers: string | string[] }[]).map((blank, j: number) => (
                            <li key={j} className="font-mono text-sm font-bold">
                              Chỗ trống [{blank.blank_index ?? j}]: {Array.isArray(blank.acceptable_answers) ? blank.acceptable_answers.join(" | ") : String(blank.acceptable_answers || "")}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {toolName === "draft_flashcards" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(Array.isArray(parsedArgs.flashcards) ? parsedArgs.flashcards : []).map((card: Record<string, unknown>, i: number) => (
                <div key={i} className="border-4 border-black p-4 shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white aspect-video flex flex-col justify-center items-center text-center text-black">
                  <h4 className="font-bold font-mono text-lg mb-2">{String(card.term || "")}</h4>
                  <p className="font-mono text-sm">{String(card.definition || "")}</p>
                </div>
              ))}
            </div>
          )}

          {toolName === "draft_topic_brief" && (
            <div className="border-4 border-black p-6 shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white font-mono whitespace-pre-wrap text-black">
              {String(parsedArgs.content || "")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
