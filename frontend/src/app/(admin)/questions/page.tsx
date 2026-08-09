"use client";

import React, { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuestions, createQuestion, updateQuestion, deleteQuestion } from "@/hooks/useQuestions";
import { useTopics } from "@/hooks/useTopics";
import type { Question, QuestionType, DifficultyLevel, Topic } from "@/types";
import { Loader2, Plus, Pencil, Trash2, X } from "lucide-react";
import MatchingBuilder, { MatchingPair } from "@/components/features/admin/MatchingBuilder";
import FillInBlankBuilder, { BlankAnswer } from "@/components/features/admin/FillInBlankBuilder";
import { toast } from "@/components/ui/toast";
import { useConfirm } from "@/hooks/useConfirm";
import { logBackendError } from "@/lib/errors";

function QuestionsContent() {
  const searchParams = useSearchParams();
  const examId = searchParams.get("exam_id");

  const [page, setPage] = useState(1);
  const [selectedTopicId, setSelectedTopicId] = useState("");
  const { topics } = useTopics({ size: 100 });
  const queryParams = examId ? { exam_id: examId, page, size: 10 } : { page, size: 10, topic_id: selectedTopicId || undefined };
  const { questions, pagination, isLoading, mutate } = useQuestions(queryParams);
  const { confirm, ConfirmDialog } = useConfirm();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  
  // Form State
  const [content, setContent] = useState("");
  const [points, setPoints] = useState(1);
  const [questionType, setQuestionType] = useState<QuestionType>("multiple_choice");
  const [difficulty, setDifficulty] = useState<DifficultyLevel>("medium");
  const [options, setOptions] = useState<{ content: string; is_correct: boolean }[]>([
    { content: "", is_correct: true },
    { content: "", is_correct: false },
  ]);
  const [matchingPairs, setMatchingPairs] = useState<MatchingPair[]>([{ left: "", right: "" }, { left: "", right: "" }]);
  const [fillInBlanks, setFillInBlanks] = useState<BlankAnswer[]>([]);

  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  
  const handleOpenModal = (q?: Question) => {
    if (q) {
      setEditingQuestionId(q.id);
      setContent(q.content);
      setPoints(q.points);
      setQuestionType(q.question_type || "SINGLE_CHOICE");
      setDifficulty(q.difficulty || "MEDIUM");
      setOptions(q.options.length ? q.options.map((opt) => ({ content: opt.content, is_correct: opt.is_correct })) : [
        { content: "", is_correct: true },
      ]);
      setMatchingPairs(q.question_type === "MATCHING" && q.metadata_json?.pairs ? (q.metadata_json.pairs as MatchingPair[]) : [{ left: "", right: "" }, { left: "", right: "" }]);
      setFillInBlanks(q.question_type === "FILL_IN_BLANK" && q.metadata_json?.blanks ? (q.metadata_json.blanks as BlankAnswer[]) : []);
    } else {
      setEditingQuestionId(null);
      setContent("");
      setPoints(1);
      setQuestionType("SINGLE_CHOICE");
      setDifficulty("MEDIUM");
      setOptions([
        { content: "", is_correct: true },
        { content: "", is_correct: false },
      ]);
      setMatchingPairs([{ left: "", right: "" }, { left: "", right: "" }]);
      setFillInBlanks([]);
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingQuestionId(null);
  };

  const handleAddOption = () => {
    setOptions([...options, { content: "", is_correct: false }]);
  };

  const handleRemoveOption = (index: number) => {
    setOptions(options.filter((_, i) => i !== index));
  };

  const handleOptionChange = (index: number, field: "content" | "is_correct", value: string | boolean) => {
    const newOptions = [...options];
    if (field === "is_correct") {
      const isSingleChoice = questionType === "single_choice" || questionType === "SINGLE_CHOICE" || questionType === "true_false";
      if (isSingleChoice && value === true) {
        newOptions.forEach((opt, i) => {
          opt.is_correct = i === index;
        });
      } else {
        newOptions[index].is_correct = value as boolean;
      }
    } else if (field === "content") {
      newOptions[index].content = value as string;
    }
    setOptions(newOptions);
  };

  const handleInsertBlank = () => {
    const textarea = document.getElementById("question_content_textarea") as HTMLTextAreaElement | null;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = content.substring(start, end).trim();

    const newContent = content.substring(0, start) + "[BLANK]" + content.substring(end);
    setContent(newContent);

    if (selectedText && questionType === "FILL_IN_BLANK") {
      const blanksBefore = (content.substring(0, start).match(/\[BLANK\]/g) || []).length;
      const newBlanks = [...fillInBlanks];
      newBlanks.splice(blanksBefore, 0, {
         blank_index: blanksBefore, 
         acceptable_answers: [selectedText]
      });
      newBlanks.forEach((b, i) => b.blank_index = i);
      setFillInBlanks(newBlanks);
    }

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + 7, start + 7);
    }, 0);
  };

  const handleSave = async () => {
    if (!content.trim()) {
      toast.add({ title: "Thông báo", description: "Question content is required.", type: "info" });
      return;
    }
    setIsSaving(true);
    try {
      let finalMetadata = null;
      let finalOptions = options;
      
      if (questionType === "MATCHING") {
        if (matchingPairs.length < 2) {
          toast.add({ title: "Thông báo", description: "Matching questions require at least 2 pairs.", type: "info" });
          setIsSaving(false);
          return;
        }
        finalMetadata = { pairs: matchingPairs };
        finalOptions = [];
      } else if (questionType === "FILL_IN_BLANK") {
        finalMetadata = { blanks: fillInBlanks };
        finalOptions = [];
      }

      const data = {
        content,
        points,
        question_type: questionType,
        difficulty,
        options: finalOptions,
        metadata_json: finalMetadata,
      };

      if (editingQuestionId) {
        await updateQuestion(editingQuestionId, data);
      } else {
        await createQuestion(data);
      }
      await mutate();
      handleCloseModal();
    } catch (error) {
      logBackendError("Question save failed", error);
      toast.add({ title: "Thông báo", description: "Failed to save question", type: "error" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!await confirm("Are you sure you want to delete this question?")) return;
    setIsDeleting(id);
    try {
      await deleteQuestion(id);
      await mutate();
    } catch (error) {
      logBackendError("Question delete failed", error);
      toast.add({ title: "Thông báo", description: "Failed to delete question", type: "error" });
    } finally {
      setIsDeleting(null);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto bg-white text-black min-h-screen">
      <div className="flex justify-between items-center mb-8 border-b-4 border-black pb-4">
        <div>
          <h1 className="text-3xl font-bold uppercase tracking-widest">Question Management</h1>
          {examId && <p className="text-sm font-mono mt-2 text-black border-2 border-black inline-block px-2 py-1 font-bold">EXAM_ID: {examId}</p>}
        </div>
        <button
          data-testid="global-add-question-button"
          onClick={() => handleOpenModal()}
          className="border-4 border-black bg-black text-white px-6 py-2 font-bold uppercase tracking-wider hover:bg-white hover:text-black transition-colors flex items-center gap-2 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px]"
        >
          <Plus size={20} />
          Add Question
        </button>
      </div>

      {!examId && (
        <div className="mb-6 flex gap-4 items-center bg-white p-4 border-4 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
          <label className="font-mono text-sm font-bold uppercase text-black">Filter by Topic:</label>
          <select
            value={selectedTopicId}
            onChange={(e) => { setSelectedTopicId(e.target.value); setPage(1); }}
            className="border-4 border-black p-2 font-mono uppercase text-sm font-bold bg-white focus:outline-none flex-1 max-w-sm"
          >
            <option value="">-- ALL TOPICS --</option>
            {topics?.map((topic: Topic) => (
              <option key={topic.id} value={topic.id}>{topic.name}</option>
            ))}
          </select>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center items-center py-20">
          <Loader2 className="animate-spin text-black" size={48} />
        </div>
      ) : questions.length === 0 ? (
        <div className="border-4 border-dashed border-black p-12 text-center bg-white">
          <p className="font-mono text-lg uppercase font-bold tracking-widest">No questions found.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {questions.map((q) => (
            <div key={q.id} className="border-4 border-black p-6 bg-white relative group shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <div className="flex flex-wrap gap-3 mb-3">
                    <span className="border-2 border-black bg-white px-2 py-1 text-xs font-mono uppercase font-bold">
                      {q.question_type?.replace(/_/g, " ") || "UNKNOWN"}
                    </span>
                    <span className="border-2 border-black bg-white px-2 py-1 text-xs font-mono uppercase font-bold">
                      PTS: {q.points}
                    </span>
                    <span className="border-2 border-black bg-white px-2 py-1 text-xs font-mono uppercase font-bold">
                      {q.difficulty || "MEDIUM"}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold whitespace-pre-wrap">{q.content}</h3>
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleOpenModal(q)}
                    className="p-2 border-4 border-black bg-white hover:bg-black hover:text-white transition-colors"
                    title="Edit"
                  >
                    <Pencil size={20} />
                  </button>
                  <button
                    onClick={() => handleDelete(q.id)}
                    disabled={isDeleting === q.id}
                    className="p-2 border-4 border-black bg-white hover:bg-black hover:text-white transition-colors disabled:opacity-50 disabled:hover:bg-white disabled:hover:text-black"
                    title="Delete"
                  >
                    {isDeleting === q.id ? <Loader2 className="animate-spin" size={20} /> : <Trash2 size={20} />}
                  </button>
                </div>
              </div>

              <div className="space-y-3 pl-4 border-l-4 border-black mt-6">
                {q.question_type === "MATCHING" && q.metadata_json && Array.isArray(q.metadata_json.pairs) ? (
                  (q.metadata_json.pairs as MatchingPair[]).map((pair, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 border-2 border-black bg-white text-black font-mono">
                      <span className="w-1/2 p-2 border-2 border-black bg-gray-50 break-words">{pair.left}</span>
                      <span className="font-bold px-2">{"->"}</span>
                      <span className="w-1/2 p-2 border-2 border-black bg-gray-50 break-words">{pair.right}</span>
                    </div>
                  ))
                ) : q.question_type === "FILL_IN_BLANK" && q.metadata_json && Array.isArray(q.metadata_json.blanks) ? (
                  (q.metadata_json.blanks as BlankAnswer[]).map((blank, i) => (
                    <div key={i} className="p-3 border-2 border-black bg-white text-black">
                      <span className="font-mono font-bold uppercase mr-3">Blank #{(blank.blank_index ?? i) + 1}:</span>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {blank.acceptable_answers && blank.acceptable_answers.length > 0 ? (
                          blank.acceptable_answers.map((ans, j) => (
                            <span key={j} className="border-2 border-black bg-black text-white px-2 py-1 text-sm font-mono font-bold">
                              {ans}
                            </span>
                          ))
                        ) : (
                          <span className="text-black italic text-sm font-mono">[No answers defined - Mock Data]</span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  q.options?.map((opt, i) => (
                    <div key={opt.id || i} className={`flex items-start gap-3 p-3 border-2 ${opt.is_correct ? 'border-black bg-black text-white font-bold' : 'border-black bg-white text-black'}`}>
                      <span className="font-mono mt-0.5">{String.fromCharCode(65 + i)}.</span>
                      <span className="flex-1 font-medium">{opt.content}</span>
                      {opt.is_correct && <span className="text-xs font-bold uppercase tracking-wider border-2 border-white bg-white text-black px-2 py-0.5">Correct</span>}
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && pagination && pagination.pages > 1 && (
        <div className="mt-8 flex justify-center gap-6 items-center font-mono">
          <button 
            disabled={page <= 1} 
            onClick={() => setPage((p) => p - 1)}
            className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors px-6 py-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold disabled:opacity-50 uppercase tracking-widest"
          >
            Prev
          </button>
          <span className="text-lg font-bold border-2 border-black px-4 py-2 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
            {page} / {pagination.pages}
          </span>
          <button 
            disabled={page >= pagination.pages} 
            onClick={() => setPage((p) => p + 1)}
            className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors px-6 py-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold disabled:opacity-50 uppercase tracking-widest"
          >
            Next
          </button>
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white border-4 border-black w-full max-w-3xl max-h-[90vh] flex flex-col shadow-[16px_16px_0px_0px_rgba(0,0,0,1)]">
            <div className="flex justify-between items-center p-6 border-b-4 border-black bg-white">
              <h2 className="text-2xl font-bold uppercase tracking-widest">
                {editingQuestionId ? "Edit Question" : "Add Question"}
              </h2>
              <button onClick={handleCloseModal} className="p-2 border-4 border-black hover:bg-black hover:text-white transition-all bg-white">
                <X size={24} />
              </button>
            </div>
            
            <div className="p-8 overflow-y-auto flex-1 space-y-8">
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black">Question Content</label>
                  {questionType === "FILL_IN_BLANK" && (
                    <button
                      type="button"
                      onClick={handleInsertBlank}
                      className="text-xs font-bold uppercase border-2 border-black bg-black text-white px-3 py-1.5 hover:bg-white hover:text-black transition-colors flex items-center gap-1 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-[2px] active:translate-y-[2px]"
                      title="Bôi đen chữ và bấm để tự động tạo [BLANK] + Đáp án"
                    >
                      <Plus size={14} /> Chèn [BLANK]
                    </button>
                  )}
                </div>
                <textarea
                  data-testid="global-question-content-input"
                  id="question_content_textarea"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full border-4 border-black p-4 min-h-[120px] focus:outline-none focus:ring-4 focus:ring-black/20 resize-y font-mono text-base bg-white"
                  placeholder="Enter question content..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-3">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black">Type</label>
                  <select
                    data-testid="global-question-type-select"
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value as QuestionType)}
                    className="w-full border-4 border-black p-3 focus:outline-none focus:ring-4 focus:ring-black/20 font-mono uppercase text-sm bg-white font-bold"
                  >
                    <option value="SINGLE_CHOICE">SINGLE CHOICE</option>
                    <option value="MULTIPLE_CHOICE">MULTIPLE CHOICE</option>
                    <option value="FILL_IN_BLANK">FILL IN BLANK</option>
                    <option value="MATCHING">MATCHING</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as DifficultyLevel)}
                    className="w-full border-4 border-black p-3 focus:outline-none focus:ring-4 focus:ring-black/20 font-mono uppercase text-sm bg-white font-bold"
                  >
                    <option value="easy">EASY</option>
                    <option value="medium">MEDIUM</option>
                    <option value="hard">HARD</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black">Points</label>
                  <input
                    data-testid="global-question-points-input"
                    type="number"
                    min="1"
                    value={points}
                    onChange={(e) => setPoints(Number(e.target.value))}
                    className="w-full border-4 border-black p-3 focus:outline-none focus:ring-4 focus:ring-black/20 font-mono font-bold bg-white"
                  />
                </div>
              </div>

              <div className="space-y-4 pt-8 border-t-4 border-black">
                {questionType === "MATCHING" ? (
                  <MatchingBuilder pairs={matchingPairs} onChange={setMatchingPairs} />
                ) : questionType === "FILL_IN_BLANK" ? (
                  <FillInBlankBuilder content={content} blanks={fillInBlanks} onChange={setFillInBlanks} />
                ) : (
                  <>
                    <div className="flex justify-between items-center">
                      <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black">Options / Answers</label>
                      <button
                        data-testid="global-add-option-button"
                        onClick={handleAddOption}
                        className="text-sm font-bold uppercase border-4 border-black bg-white px-4 py-2 hover:bg-black hover:text-white transition-colors flex items-center gap-2 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px]"
                      >
                        <Plus size={16} /> Add Option
                      </button>
                    </div>
                    
                    {options.map((opt, i) => (
                      <div key={i} className={`flex items-start gap-4 p-4 border-4 ${opt.is_correct ? 'border-black bg-gray-50' : 'border-dashed border-black bg-white'}`}>
                        <span className="font-mono text-xl mt-2 w-8 font-bold">{String.fromCharCode(65 + i)}.</span>
                        <input
                          data-testid="global-option-content-input"
                          type="text"
                          value={opt.content}
                          onChange={(e) => handleOptionChange(i, "content", e.target.value)}
                          className="flex-1 border-4 border-black p-3 focus:outline-none focus:ring-4 focus:ring-black/20 font-mono text-base bg-white"
                          placeholder="Option text..."
                        />
                        <label className="flex items-center gap-3 mt-3 cursor-pointer select-none">
                          <input
                            type={questionType === "MULTIPLE_CHOICE" ? "checkbox" : "radio"}
                            name={`correct_option_${editingQuestionId || 'new'}`}
                            checked={opt.is_correct}
                            onChange={(e) => handleOptionChange(i, "is_correct", e.target.checked)}
                            className="w-6 h-6 accent-black cursor-pointer border-4 border-black"
                          />
                          <span className="text-sm font-bold uppercase tracking-widest font-mono text-black">Correct</span>
                        </label>
                        <button
                          onClick={() => handleRemoveOption(i)}
                          className="mt-2 p-2 border-4 border-black bg-white hover:bg-black hover:text-white transition-all"
                          title="Remove Option"
                        >
                          <Trash2 size={20} />
                        </button>
                      </div>
                    ))}
                    {options.length === 0 && (
                      <p className="text-base font-mono text-black font-bold uppercase tracking-widest text-center py-12 border-4 border-dashed border-black bg-white">
                        No options added yet. Click &quot;Add Option&quot; to begin.
                      </p>
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="p-6 border-t-4 border-black flex justify-end gap-6 bg-white">
              <button
                onClick={handleCloseModal}
                disabled={isSaving}
                className="px-8 py-3 border-4 border-black bg-white font-bold uppercase tracking-widest hover:bg-gray-100 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                data-testid="global-save-question-button"
                onClick={handleSave}
                disabled={isSaving}
                className="px-8 py-3 border-4 border-black bg-black text-white font-bold uppercase tracking-widest hover:bg-white hover:text-black transition-colors disabled:opacity-50 flex items-center gap-3 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px]"
              >
                {isSaving && <Loader2 className="animate-spin" size={20} />}
                {editingQuestionId ? "Save Changes" : "Create Question"}
              </button>
            </div>
          </div>
        </div>
      )}
      <ConfirmDialog />
    </div>
  );
}

export default function QuestionsPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen items-center justify-center bg-white text-black">
        <Loader2 className="animate-spin" size={48} />
      </div>
    }>
      <QuestionsContent />
    </Suspense>
  );
}
