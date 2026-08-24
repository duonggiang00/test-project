"use client";

import React, { useCallback, useState } from "react";
import { Loader2 } from "lucide-react";
import GenerationJobReview from "./GenerationJobReview";
import { toast } from "@/components/ui/toast";
import { getBackendErrorMessage, logBackendError } from "@/lib/errors";
import { useGenerationJobReview } from "@/hooks/useMaterialWorkspace";
import type {
  FlashcardDraftPayload,
  QuestionDraftPayload,
} from "@/services/apiService";

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

type EditableOption = { content: string; is_correct: boolean };

type EditableQuestion = {
  type: string;
  content: string;
  points: number;
  difficulty: string;
  source_reference: string | null;
  explanation: string | null;
  options: EditableOption[];
  metadata_json: Record<string, unknown> | null;
};

type EditableFlashcard = {
  term: string;
  definition: string;
  source_reference: string | null;
  explanation: string | null;
};

function toEditableQuestion(raw: Record<string, unknown>): EditableQuestion {
  const options = Array.isArray(raw.options) ? raw.options : [];
  return {
    type: typeof raw.type === "string" ? raw.type : "SINGLE_CHOICE",
    content: typeof raw.content === "string" ? raw.content : "",
    points: typeof raw.points === "number" ? raw.points : 1,
    difficulty: typeof raw.difficulty === "string" ? raw.difficulty : "MEDIUM",
    source_reference:
      typeof raw.source_reference === "string" ? raw.source_reference : null,
    explanation: typeof raw.explanation === "string" ? raw.explanation : null,
    options: options.map((opt) => {
      const o = opt as Record<string, unknown>;
      return {
        content: typeof o.content === "string" ? o.content : "",
        is_correct: Boolean(o.is_correct),
      };
    }),
    metadata_json:
      raw.metadata_json && typeof raw.metadata_json === "object"
        ? (raw.metadata_json as Record<string, unknown>)
        : null,
  };
}

function toEditableFlashcard(raw: Record<string, unknown>): EditableFlashcard {
  return {
    term: typeof raw.term === "string" ? raw.term : "",
    definition: typeof raw.definition === "string" ? raw.definition : "",
    source_reference:
      typeof raw.source_reference === "string" ? raw.source_reference : null,
    explanation: typeof raw.explanation === "string" ? raw.explanation : null,
  };
}

function makeBlankQuestion(): EditableQuestion {
  return {
    type: "SINGLE_CHOICE",
    content: "",
    points: 1,
    difficulty: "MEDIUM",
    source_reference: null,
    explanation: null,
    options: [
      { content: "", is_correct: true },
      { content: "", is_correct: false },
      { content: "", is_correct: false },
      { content: "", is_correct: false },
    ],
    metadata_json: null,
  };
}

function makeBlankFlashcard(): EditableFlashcard {
  return { term: "", definition: "", source_reference: null, explanation: null };
}

function toQuestionPayload(q: EditableQuestion): QuestionDraftPayload {
  return {
    type: q.type,
    content: q.content,
    points: q.points,
    difficulty: q.difficulty,
    source_reference: q.source_reference,
    explanation: q.explanation,
    options: q.options,
    metadata_json: q.metadata_json,
  };
}

function toFlashcardPayload(c: EditableFlashcard): FlashcardDraftPayload {
  return {
    term: c.term,
    definition: c.definition,
    source_reference: c.source_reference,
    explanation: c.explanation,
  };
}

const CARD_CLASS =
  "border-4 border-black p-4 shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white text-black";

const INPUT_CLASS =
  "w-full border-2 border-black p-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black/30 bg-white text-black";

const SMALL_BUTTON_CLASS =
  "px-2 py-1 border-2 border-black font-mono font-bold text-xs uppercase " +
  "hover:bg-black hover:text-white transition-none disabled:opacity-50 disabled:cursor-not-allowed";

const PRIMARY_BUTTON_CLASS =
  "px-4 py-2 border-4 border-black font-mono font-bold text-xs uppercase " +
  "bg-black text-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-white hover:text-black " +
  "disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2";

export default function GenerativePreview({ toolName, toolArgs, isStreaming }: GenerativePreviewProps) {
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
      : (toolName ? DEFAULT_PUBLISH_TITLES[toolName] : null) ?? null;

  const handleDraftError = useCallback((caught: unknown) => {
    logBackendError("AI generation draft update failed", caught);
    toast.add({
      title: "Lưu thất bại",
      description: getBackendErrorMessage(
        caught,
        "Không thể lưu thay đổi bản nháp.",
      ),
      type: "error",
    });
  }, []);

  const { job, updateDraft, isSavingDraft } = useGenerationJobReview(
    jobId,
    handleDraftError,
  );

  // A draft is only editable while a reviewer hasn't decided on it yet --
  // `MaterialService.update_generation_job_draft` refuses the edit outright
  // once the job leaves `awaiting_review`, so the UI never offers a control
  // the server is guaranteed to reject.
  const isEditable = Boolean(jobId) && !isStreaming && job?.status === "awaiting_review";

  const [seededJobId, setSeededJobId] = useState<string | null>(null);
  const [editedQuestions, setEditedQuestions] = useState<EditableQuestion[] | null>(null);
  const [editedFlashcards, setEditedFlashcards] = useState<EditableFlashcard[] | null>(null);
  const [editedBriefContent, setEditedBriefContent] = useState<string | null>(null);
  const [editedBriefTitle, setEditedBriefTitle] = useState<string>("");

  // Reset local edits when the panel starts showing a different job (a new
  // generation, or none at all) so a stale edited draft never bleeds into
  // it, then seed local edit state from the job's authoritative draft
  // exactly once per job. Both are "adjust state during render" per React's
  // own guidance (https://react.dev/learn/you-might-not-need-an-effect) --
  // calling setState here, guarded by a comparison against state captured
  // from a previous render, replaces the render React was about to commit
  // rather than causing an extra effect-triggered render afterwards.
  if (jobId !== seededJobId) {
    setSeededJobId(jobId);
    setEditedQuestions(null);
    setEditedFlashcards(null);
    setEditedBriefContent(null);
    setEditedBriefTitle("");
  } else if (job && job.id === jobId) {
    const draft = (job.draft_payload ?? {}) as Record<string, unknown>;
    if (
      toolName === "draft_exam" &&
      editedQuestions === null &&
      Array.isArray(draft.questions)
    ) {
      setEditedQuestions(
        (draft.questions as Record<string, unknown>[]).map(toEditableQuestion),
      );
    } else if (
      toolName === "draft_flashcards" &&
      editedFlashcards === null &&
      Array.isArray(draft.flashcards)
    ) {
      setEditedFlashcards(
        (draft.flashcards as Record<string, unknown>[]).map(toEditableFlashcard),
      );
    } else if (
      toolName === "draft_topic_brief" &&
      editedBriefContent === null &&
      typeof draft.content === "string"
    ) {
      setEditedBriefContent(draft.content);
      setEditedBriefTitle(typeof draft.title === "string" ? draft.title : "");
    }
  }

  const updateQuestion = useCallback(
    (index: number, patch: Partial<EditableQuestion>) => {
      setEditedQuestions((prev) =>
        prev ? prev.map((q, i) => (i === index ? { ...q, ...patch } : q)) : prev,
      );
    },
    [],
  );

  const updateOption = useCallback(
    (qIndex: number, optIndex: number, patch: Partial<EditableOption>) => {
      setEditedQuestions((prev) =>
        prev
          ? prev.map((q, i) =>
              i === qIndex
                ? {
                    ...q,
                    options: q.options.map((opt, j) =>
                      j === optIndex ? { ...opt, ...patch } : opt,
                    ),
                  }
                : q,
            )
          : prev,
      );
    },
    [],
  );

  const toggleOptionCorrect = useCallback((qIndex: number, optIndex: number) => {
    setEditedQuestions((prev) =>
      prev
        ? prev.map((q, i) => {
            if (i !== qIndex) return q;
            const singleChoice = q.type === "SINGLE_CHOICE";
            return {
              ...q,
              options: q.options.map((opt, j) =>
                singleChoice
                  ? { ...opt, is_correct: j === optIndex }
                  : j === optIndex
                    ? { ...opt, is_correct: !opt.is_correct }
                    : opt,
              ),
            };
          })
        : prev,
    );
  }, []);

  const addOption = useCallback((qIndex: number) => {
    setEditedQuestions((prev) =>
      prev
        ? prev.map((q, i) =>
            i === qIndex
              ? { ...q, options: [...q.options, { content: "", is_correct: false }] }
              : q,
          )
        : prev,
    );
  }, []);

  const removeOption = useCallback((qIndex: number, optIndex: number) => {
    setEditedQuestions((prev) =>
      prev
        ? prev.map((q, i) =>
            i === qIndex
              ? { ...q, options: q.options.filter((_, j) => j !== optIndex) }
              : q,
          )
        : prev,
    );
  }, []);

  const addQuestion = useCallback(() => {
    setEditedQuestions((prev) => [...(prev ?? []), makeBlankQuestion()]);
  }, []);

  const removeQuestion = useCallback((qIndex: number) => {
    setEditedQuestions((prev) => (prev ? prev.filter((_, i) => i !== qIndex) : prev));
  }, []);

  const clearQuestions = useCallback(() => {
    setEditedQuestions([]);
  }, []);

  const saveQuestions = useCallback(async () => {
    if (!editedQuestions) return;
    try {
      await updateDraft({ questions: editedQuestions.map(toQuestionPayload) });
      toast.add({
        title: "Đã lưu",
        description: "Đã lưu thay đổi bản nháp câu hỏi.",
        type: "success",
      });
    } catch {
      // handleDraftError already reported this via the hook's onError.
    }
  }, [editedQuestions, updateDraft]);

  const updateFlashcard = useCallback(
    (index: number, patch: Partial<EditableFlashcard>) => {
      setEditedFlashcards((prev) =>
        prev ? prev.map((c, i) => (i === index ? { ...c, ...patch } : c)) : prev,
      );
    },
    [],
  );

  const addFlashcard = useCallback(() => {
    setEditedFlashcards((prev) => [...(prev ?? []), makeBlankFlashcard()]);
  }, []);

  const removeFlashcard = useCallback((index: number) => {
    setEditedFlashcards((prev) => (prev ? prev.filter((_, i) => i !== index) : prev));
  }, []);

  const clearFlashcards = useCallback(() => {
    setEditedFlashcards([]);
  }, []);

  const saveFlashcards = useCallback(async () => {
    if (!editedFlashcards) return;
    try {
      await updateDraft({ flashcards: editedFlashcards.map(toFlashcardPayload) });
      toast.add({
        title: "Đã lưu",
        description: "Đã lưu thay đổi bản nháp flashcard.",
        type: "success",
      });
    } catch {
      // handleDraftError already reported this via the hook's onError.
    }
  }, [editedFlashcards, updateDraft]);

  const saveBrief = useCallback(async () => {
    if (editedBriefContent === null) return;
    try {
      await updateDraft({
        content: editedBriefContent,
        title: editedBriefTitle || null,
      });
      toast.add({
        title: "Đã lưu",
        description: "Đã lưu thay đổi bản nháp tóm tắt.",
        type: "success",
      });
    } catch {
      // handleDraftError already reported this via the hook's onError.
    }
  }, [editedBriefContent, editedBriefTitle, updateDraft]);

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

  const questionsToRender: EditableQuestion[] =
    editedQuestions ??
    (Array.isArray(parsedArgs?.questions)
      ? (parsedArgs.questions as Record<string, unknown>[]).map(toEditableQuestion)
      : []);
  const flashcardsToRender: EditableFlashcard[] =
    editedFlashcards ??
    (Array.isArray(parsedArgs?.flashcards)
      ? (parsedArgs.flashcards as Record<string, unknown>[]).map(toEditableFlashcard)
      : []);
  const briefContentToRender =
    editedBriefContent ??
    (typeof parsedArgs?.content === "string" ? parsedArgs.content : "");

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
        {isEditable && (
          <p className="font-mono text-xs font-bold uppercase bg-white border-2 border-black p-2">
            [EDIT] Bạn có thể chỉnh sửa, xóa hoặc thêm nội dung bên dưới trước khi duyệt.
          </p>
        )}
      </div>

      {!parsedArgs && editedQuestions === null && editedFlashcards === null && editedBriefContent === null ? (
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
                {typeof parsedArgs?.title === "string" ? parsedArgs.title : "Untitled Exam"}
              </h4>

              {isEditable && (
                <div className="flex flex-wrap gap-2 mb-4">
                  <button type="button" className={SMALL_BUTTON_CLASS} onClick={addQuestion}>
                    + Thêm câu hỏi
                  </button>
                  <button type="button" className={SMALL_BUTTON_CLASS} onClick={clearQuestions}>
                    Xóa tất cả
                  </button>
                  <button
                    type="button"
                    className={PRIMARY_BUTTON_CLASS}
                    onClick={saveQuestions}
                    disabled={isSavingDraft}
                    aria-busy={isSavingDraft}
                  >
                    {isSavingDraft && <Loader2 className="animate-spin w-4 h-4" aria-hidden="true" />}
                    Lưu thay đổi
                  </button>
                </div>
              )}

              <div className="space-y-4">
                {questionsToRender.length === 0 && (
                  <p className="font-mono text-sm opacity-60">Chưa có câu hỏi nào.</p>
                )}
                {questionsToRender.map((q, i) => {
                  const isChoiceType = q.type === "SINGLE_CHOICE" || q.type === "MULTIPLE_CHOICE";
                  return (
                    <div key={i} className={CARD_CLASS}>
                      <div className="flex justify-between items-start mb-2 gap-2">
                        {isEditable ? (
                          <textarea
                            className={`${INPUT_CLASS} flex-1`}
                            value={q.content}
                            onChange={(e) => updateQuestion(i, { content: e.target.value })}
                            placeholder={`Nội dung câu hỏi ${i + 1}`}
                            rows={2}
                          />
                        ) : (
                          <span className="font-bold font-mono">Q{i + 1}. {q.content}</span>
                        )}
                        <div className="flex flex-col gap-2 items-end">
                          <div className="flex gap-2">
                            {isEditable ? (
                              <select
                                className="border-2 border-black font-mono text-xs font-bold uppercase p-1"
                                value={q.difficulty}
                                onChange={(e) => updateQuestion(i, { difficulty: e.target.value })}
                              >
                                <option value="EASY">EASY</option>
                                <option value="MEDIUM">MEDIUM</option>
                                <option value="HARD">HARD</option>
                              </select>
                            ) : (
                              <span className="bg-white border-2 border-black px-2 py-1 text-xs font-mono font-bold uppercase shadow-[2px_2px_0_0_rgba(0,0,0,1)]">{q.difficulty}</span>
                            )}
                            {isEditable && isChoiceType ? (
                              <select
                                className="border-2 border-black font-mono text-xs font-bold uppercase p-1"
                                value={q.type}
                                onChange={(e) => updateQuestion(i, { type: e.target.value })}
                              >
                                <option value="SINGLE_CHOICE">SINGLE_CHOICE</option>
                                <option value="MULTIPLE_CHOICE">MULTIPLE_CHOICE</option>
                              </select>
                            ) : (
                              <span className="bg-black text-white border-2 border-black px-2 py-1 text-xs font-mono font-bold uppercase shadow-[2px_2px_0_0_rgba(0,0,0,1)]">{q.type}</span>
                            )}
                          </div>
                          {isEditable && (
                            <button
                              type="button"
                              className={SMALL_BUTTON_CLASS}
                              onClick={() => removeQuestion(i)}
                            >
                              Xóa câu hỏi
                            </button>
                          )}
                        </div>
                      </div>

                      {isChoiceType && (
                        <ul className="mt-2 space-y-2 border-t-2 border-black pt-2">
                          {q.options.map((opt, j) => (
                            <li key={j} className="flex items-center gap-2 font-mono text-sm font-bold">
                              {isEditable ? (
                                <>
                                  <input
                                    type={q.type === "SINGLE_CHOICE" ? "radio" : "checkbox"}
                                    name={`q-${i}-correct`}
                                    checked={opt.is_correct}
                                    onChange={() => toggleOptionCorrect(i, j)}
                                    className="w-4 h-4"
                                  />
                                  <input
                                    className={`${INPUT_CLASS} flex-1`}
                                    value={opt.content}
                                    onChange={(e) => updateOption(i, j, { content: e.target.value })}
                                    placeholder={`Đáp án ${j + 1}`}
                                  />
                                  <button
                                    type="button"
                                    className={SMALL_BUTTON_CLASS}
                                    onClick={() => removeOption(i, j)}
                                  >
                                    Xóa
                                  </button>
                                </>
                              ) : (
                                <>
                                  <span className="material-symbols-outlined text-base font-bold">
                                    {opt.is_correct ? "check_box" : "check_box_outline_blank"}
                                  </span>
                                  {opt.content}
                                </>
                              )}
                            </li>
                          ))}
                          {isEditable && (
                            <li>
                              <button
                                type="button"
                                className={SMALL_BUTTON_CLASS}
                                onClick={() => addOption(i)}
                              >
                                + Thêm đáp án
                              </button>
                            </li>
                          )}
                        </ul>
                      )}

                      {q.type === "MATCHING" && !!q.metadata_json && !!q.metadata_json.pairs && (
                        <div className="mt-2 border-t-2 border-black pt-2">
                          <p className="text-xs font-mono font-bold uppercase mb-2 underline">Các cặp ghép nối:</p>
                          <ul className="space-y-1">
                            {(q.metadata_json.pairs as Record<string, string>[]).map((pair, j) => (
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
                      {q.type === "FILL_IN_BLANK" && !!q.metadata_json && !!q.metadata_json.blanks && (
                        <div className="mt-2 border-t-2 border-black pt-2">
                          <p className="text-xs font-mono font-bold uppercase mb-2 underline">Các chỗ trống cần điền:</p>
                          <ul className="space-y-1">
                            {(q.metadata_json.blanks as { blank_index?: number; acceptable_answers: string | string[] }[]).map((blank, j) => (
                              <li key={j} className="font-mono text-sm font-bold">
                                Chỗ trống [{blank.blank_index ?? j}]: {Array.isArray(blank.acceptable_answers) ? blank.acceptable_answers.join(" | ") : String(blank.acceptable_answers || "")}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {toolName === "draft_flashcards" && (
            <div>
              {isEditable && (
                <div className="flex flex-wrap gap-2 mb-4">
                  <button type="button" className={SMALL_BUTTON_CLASS} onClick={addFlashcard}>
                    + Thêm thẻ
                  </button>
                  <button type="button" className={SMALL_BUTTON_CLASS} onClick={clearFlashcards}>
                    Xóa tất cả
                  </button>
                  <button
                    type="button"
                    className={PRIMARY_BUTTON_CLASS}
                    onClick={saveFlashcards}
                    disabled={isSavingDraft}
                    aria-busy={isSavingDraft}
                  >
                    {isSavingDraft && <Loader2 className="animate-spin w-4 h-4" aria-hidden="true" />}
                    Lưu thay đổi
                  </button>
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {flashcardsToRender.length === 0 && (
                  <p className="font-mono text-sm opacity-60">Chưa có thẻ nào.</p>
                )}
                {flashcardsToRender.map((card, i) => (
                  <div key={i} className={`${CARD_CLASS} flex flex-col justify-center items-stretch text-center gap-2`}>
                    {isEditable ? (
                      <>
                        <input
                          className={`${INPUT_CLASS} font-bold text-center`}
                          value={card.term}
                          onChange={(e) => updateFlashcard(i, { term: e.target.value })}
                          placeholder="Thuật ngữ"
                        />
                        <textarea
                          className={`${INPUT_CLASS} text-center`}
                          value={card.definition}
                          onChange={(e) => updateFlashcard(i, { definition: e.target.value })}
                          placeholder="Định nghĩa"
                          rows={2}
                        />
                        <button
                          type="button"
                          className={SMALL_BUTTON_CLASS}
                          onClick={() => removeFlashcard(i)}
                        >
                          Xóa thẻ
                        </button>
                      </>
                    ) : (
                      <>
                        <h4 className="font-bold font-mono text-lg mb-2">{card.term}</h4>
                        <p className="font-mono text-sm">{card.definition}</p>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {toolName === "draft_topic_brief" && (
            <div>
              {isEditable ? (
                <div className={CARD_CLASS}>
                  <input
                    className={`${INPUT_CLASS} font-bold mb-2`}
                    value={editedBriefTitle}
                    onChange={(e) => setEditedBriefTitle(e.target.value)}
                    placeholder="Tiêu đề tóm tắt"
                  />
                  <textarea
                    className={`${INPUT_CLASS} whitespace-pre-wrap`}
                    value={briefContentToRender}
                    onChange={(e) => setEditedBriefContent(e.target.value)}
                    rows={12}
                  />
                  <div className="flex flex-wrap gap-2 mt-3">
                    <button
                      type="button"
                      className={SMALL_BUTTON_CLASS}
                      onClick={() => setEditedBriefContent("")}
                    >
                      Xóa nội dung
                    </button>
                    <button
                      type="button"
                      className={PRIMARY_BUTTON_CLASS}
                      onClick={saveBrief}
                      disabled={isSavingDraft}
                      aria-busy={isSavingDraft}
                    >
                      {isSavingDraft && <Loader2 className="animate-spin w-4 h-4" aria-hidden="true" />}
                      Lưu thay đổi
                    </button>
                  </div>
                </div>
              ) : (
                <div className="border-4 border-black p-6 shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white font-mono whitespace-pre-wrap text-black">
                  {briefContentToRender}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
