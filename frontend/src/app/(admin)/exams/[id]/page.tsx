"use client";

import React, { useState, use } from "react";
import { useExamDetail } from "@/hooks/useExams";
import { updateQuestion, deleteQuestion, useQuestions } from "@/hooks/useQuestions";
import { useTopics } from "@/hooks/useTopics";
import { bulkAddQuestionsToExam } from "@/services/apiService";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { createExamQuestion } from "@/hooks/useExams";
import type { Question, QuestionType, DifficultyLevel, Topic } from "@/types";
import { Loader2, ArrowLeft, Plus, Pencil, Trash2, X } from "lucide-react";
import MatchingBuilder, { MatchingPair } from "@/components/features/admin/MatchingBuilder";
import FillInBlankBuilder, { BlankAnswer } from "@/components/features/admin/FillInBlankBuilder";
import Link from "next/link";
import { notFound } from "next/navigation";
import { toast } from "@/components/ui/toast";
import { useConfirm } from "@/hooks/useConfirm";
import { logBackendError } from "@/lib/errors";
import { toCanonicalDifficulty, toCanonicalQuestionType } from "@/lib/questionEnums";

export default function ExamDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const unwrappedParams = use(params);
  const { exam, isLoading: isLoadingExam, isError, mutate } = useExamDetail(unwrappedParams.id);
  
  const questions = exam?.questions || [];
  const { confirm, ConfirmDialog } = useConfirm();

  // Global questions for "Ngân Hàng Câu Hỏi"
  const [globalPage, setGlobalPage] = useState(1);
  const [globalTopicId, setGlobalTopicId] = useState<string | null>(null);
  const { topics: globalTopics } = useTopics({ size: 100 });
  const effectiveGlobalTopicId = globalTopicId ?? exam?.topic_id ?? "";
  const {
    questions: globalQuestions,
    pagination: globalPagination,
    isLoading: isLoadingGlobal,
    mutate: mutateGlobalQuestions,
  } = useQuestions({
    page: globalPage,
    size: 10,
    topic_id: effectiveGlobalTopicId || undefined,
  });
  const [selectedGlobalQuestionIds, setSelectedGlobalQuestionIds] = useState<string[]>([]);
  const [isAddingBulk, setIsAddingBulk] = useState(false);
  const existingQuestionIds = new Set(questions.map((question) => question.id));
  const availableGlobalQuestions = globalQuestions.filter(
    (question) => !existingQuestionIds.has(question.id),
  );

  const toggleGlobalQuestionSelect = (id: string) => {
    setSelectedGlobalQuestionIds(prev => 
      prev.includes(id) ? prev.filter(qId => qId !== id) : [...prev, id]
    );
  };

  const handleBulkAdd = async () => {
    if (selectedGlobalQuestionIds.length === 0) return;
    setIsAddingBulk(true);
    try {
      await bulkAddQuestionsToExam(exam!.id, selectedGlobalQuestionIds);
      toast.add({ title: "Thành công", description: `Đã thêm ${selectedGlobalQuestionIds.length} câu hỏi vào đề thi.`, type: "success" });
      setSelectedGlobalQuestionIds([]);
      await Promise.all([mutate(), mutateGlobalQuestions()]);
    } catch (error) {
      logBackendError("Exam question bulk add failed", error);
      toast.add({ title: "Lỗi", description: "Không thể thêm câu hỏi", type: "error" });
    } finally {
      setIsAddingBulk(false);
    }
  };

  // Question Form State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [points, setPoints] = useState(1);
  const [questionType, setQuestionType] = useState<QuestionType>("MULTIPLE_CHOICE");
  const [difficulty, setDifficulty] = useState<DifficultyLevel>("MEDIUM");
  const [options, setOptions] = useState<{ content: string; is_correct: boolean }[]>([
    { content: "", is_correct: true },
    { content: "", is_correct: false },
  ]);
  const [matchingPairs, setMatchingPairs] = useState<MatchingPair[]>([{ left: "", right: "" }, { left: "", right: "" }]);
  const [fillInBlanks, setFillInBlanks] = useState<BlankAnswer[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  if (isLoadingExam) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  if (isError || !exam) {
    return notFound();
  }

  // Form Handlers
  const handleOpenModal = (q?: Question) => {
    if (q) {
      setEditingQuestionId(q.id);
      setContent(q.content);
      setPoints(q.points);
      setQuestionType(toCanonicalQuestionType(q.question_type));
      setDifficulty(toCanonicalDifficulty(q.difficulty));
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
      const isSingleChoice = questionType === "SINGLE_CHOICE"
        || questionType === "single_choice"
        || questionType === "true_false";
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
    const textarea = document.getElementById("exam_question_content_textarea") as HTMLTextAreaElement | null;
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
        question_type: toCanonicalQuestionType(questionType),
        difficulty: toCanonicalDifficulty(difficulty),
        options: finalOptions,
        metadata_json: finalMetadata,
        exam_id: exam.id,
      };

      if (editingQuestionId) {
        await updateQuestion(editingQuestionId, data);
      } else {
        await createExamQuestion(exam.id, data);
      }
      await mutate(); // trigger refresh of exam detail
      handleCloseModal();
    } catch (error) {
      logBackendError("Exam question save failed", error);
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
      logBackendError("Exam question delete failed", error);
      toast.add({ title: "Thông báo", description: "Failed to delete question", type: "error" });
    } finally {
      setIsDeleting(null);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto bg-white text-black min-h-screen">
      <div className="flex items-center gap-6 border-b-4 border-black pb-6 mb-8">
        <Link 
          href="/exams"
          className="p-3 border-4 border-black hover:bg-black hover:text-white transition-colors flex items-center justify-center bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px]"
        >
          <ArrowLeft className="w-6 h-6" />
        </Link>
        <div>
          <h1 className="text-3xl font-bold uppercase tracking-widest font-mono">Chi Tiết Đề Thi</h1>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cột trái: Thông tin đề thi */}
        <div className="lg:col-span-1 space-y-8">
          <div className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
            <h2 className="text-xl font-bold uppercase tracking-widest font-mono mb-6 border-b-4 border-black pb-4">Thông tin chung</h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black mb-2">Tiêu đề</label>
                <div className="font-bold text-xl">{exam.title}</div>
              </div>
              <div>
                <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black mb-2">Thời gian</label>
                <div className="font-mono text-lg font-bold">{exam.duration_minutes} PHÚT</div>
              </div>
              <div>
                <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black mb-2">Trạng thái</label>
                <div className={`inline-block px-3 py-1 font-bold text-sm uppercase font-mono border-2 border-black ${exam.is_published ? 'bg-black text-white' : 'bg-white text-black'}`}>
                  {exam.is_published ? "ĐÃ XUẤT BẢN" : "BẢN NHÁP"}
                </div>
              </div>
              <div>
                <label className="block text-sm font-bold uppercase tracking-widest font-mono text-black mb-2">Mô tả</label>
                <div className="text-base font-mono">{exam.description || "Không có mô tả"}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Cột phải: Danh sách câu hỏi */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="exam_questions" className="w-full">
            <TabsList className="w-full justify-start border-b-4 border-black bg-transparent p-0 h-auto rounded-none flex mb-8">
              <TabsTrigger 
                value="exam_questions"
                className="rounded-none border-t-4 border-l-4 border-r-4 border-black bg-gray-200 data-[state=active]:bg-white data-[state=active]:text-black font-mono font-bold uppercase py-3 px-6 -mb-1 flex-1 sm:flex-none data-[state=active]:border-b-white z-10"
              >
                Câu Hỏi Đề Thi ({questions.length})
              </TabsTrigger>
              <TabsTrigger 
                value="question_bank"
                className="rounded-none border-t-4 border-r-4 border-black border-l-0 sm:border-l-4 bg-gray-200 data-[state=active]:bg-white data-[state=active]:text-black font-mono font-bold uppercase py-3 px-6 -mb-1 flex-1 sm:flex-none data-[state=active]:border-b-white z-10"
              >
                Ngân Hàng Câu Hỏi
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="exam_questions" className="m-0 outline-none space-y-8">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-2xl font-bold uppercase tracking-widest font-mono">Danh sách Câu hỏi ({questions.length})</h2>
                <button
              data-testid="add-question-button"
              onClick={() => handleOpenModal()}
              className="flex items-center gap-3 border-4 border-black bg-black text-white px-6 py-3 font-bold uppercase font-mono tracking-widest hover:bg-white hover:text-black transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px]"
            >
              <Plus size={20} /> Thêm Câu hỏi
            </button>
          </div>

          {questions.length === 0 ? (
            <div className="p-16 border-4 border-dashed border-black text-center bg-white">
              <p className="font-bold uppercase font-mono tracking-widest text-lg text-black mb-4">Chưa có câu hỏi nào trong đề thi này.</p>
              <p className="text-sm font-mono text-black">Bấm &quot;Thêm Câu hỏi&quot; để bắt đầu xây dựng nội dung.</p>
            </div>
          ) : (
            <div className="space-y-8">
              {questions.map((q, index) => (
                <div key={q.id} className="border-4 border-black p-6 bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] group">
                  <div className="flex justify-between items-start mb-6">
                    <div className="flex-1 pr-6">
                      <div className="flex gap-3 mb-4 flex-wrap">
                        <span className="border-2 border-black px-3 py-1 text-sm font-bold uppercase font-mono bg-white">CÂU {index + 1}</span>
                        <span className="border-2 border-black px-3 py-1 text-sm font-bold uppercase font-mono bg-white">{q.points} ĐIỂM</span>
                        <span className="border-2 border-black px-3 py-1 text-sm font-bold uppercase font-mono bg-white">{q.question_type?.replace(/_/g, " ")}</span>
                      </div>
                      <h3 className="text-xl font-bold whitespace-pre-wrap">{q.content}</h3>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => handleOpenModal(q)}
                        className="p-3 border-4 border-black hover:bg-black hover:text-white transition-colors bg-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] active:shadow-none active:translate-x-[2px] active:translate-y-[2px]"
                        title="Sửa"
                      >
                        <Pencil size={20} />
                      </button>
                      <button
                        data-testid="delete-question-button"
                        onClick={() => handleDelete(q.id)}
                        disabled={isDeleting === q.id}
                        className="p-3 border-4 border-black hover:bg-black hover:text-white transition-colors bg-white disabled:opacity-50 disabled:hover:bg-white disabled:hover:text-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] active:shadow-none active:translate-x-[2px] active:translate-y-[2px]"
                        title="Xóa"
                      >
                        {isDeleting === q.id ? <Loader2 size={20} className="animate-spin" /> : <Trash2 size={20} />}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3 mt-6 border-t-4 border-black pt-6">
                    {q.question_type === "MATCHING" && q.metadata_json && Array.isArray(q.metadata_json.pairs) ? (
                      (q.metadata_json.pairs as MatchingPair[]).map((pair, i) => (
                        <div key={i} className="flex items-center gap-3 p-3 border-2 border-black bg-white text-base font-mono font-bold">
                          <span className="w-1/2 p-2 border-2 border-black bg-white break-words">{pair.left}</span>
                          <span className="font-bold px-2">{"->"}</span>
                          <span className="w-1/2 p-2 border-2 border-black bg-white break-words">{pair.right}</span>
                        </div>
                      ))
                    ) : q.question_type === "FILL_IN_BLANK" && q.metadata_json && Array.isArray(q.metadata_json.blanks) ? (
                      (q.metadata_json.blanks as BlankAnswer[]).map((blank, i) => (
                        <div key={i} className="p-4 border-2 border-black bg-white text-base">
                          <span className="font-bold uppercase font-mono mr-3 tracking-widest">Blank #{(blank.blank_index ?? i) + 1}:</span>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {blank.acceptable_answers && blank.acceptable_answers.length > 0 ? (
                              blank.acceptable_answers.map((ans, j) => (
                                <span key={j} className="border-2 border-black bg-black text-white px-2.5 py-1 text-sm font-bold font-mono">
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
                        <div key={opt.id || i} className={`flex items-start gap-4 p-4 border-4 ${opt.is_correct ? 'border-black bg-black text-white' : 'border-black bg-white'}`}>
                          <span className="font-bold font-mono text-xl w-8">{String.fromCharCode(65 + i)}.</span>
                          <span className="flex-1 font-bold font-mono text-lg">{opt.content}</span>
                          {opt.is_correct && <span className="text-xs font-bold uppercase tracking-wider border-2 border-white bg-white text-black px-2 py-0.5 font-mono">Correct</span>}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
            </TabsContent>

            <TabsContent value="question_bank" className="m-0 outline-none">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
                <div className="flex gap-4 items-center bg-white p-3 border-4 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] flex-1">
                  <label htmlFor="exam-question-bank-topic-filter" className="font-mono text-sm font-bold uppercase text-black whitespace-nowrap">Lọc theo Chủ đề:</label>
                  <select
                    id="exam-question-bank-topic-filter"
                    value={effectiveGlobalTopicId}
                    onChange={(e) => { setGlobalTopicId(e.target.value); setGlobalPage(1); }}
                    className="border-4 border-black p-2 font-mono uppercase text-sm font-bold bg-white focus:outline-none w-full"
                  >
                    <option value="">-- TẤT CẢ CHỦ ĐỀ --</option>
                    {globalTopics?.map((topic: Topic) => (
                      <option key={topic.id} value={topic.id}>{topic.name}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleBulkAdd}
                  disabled={selectedGlobalQuestionIds.length === 0 || isAddingBulk}
                  className="border-4 border-black bg-white text-black px-6 py-3 font-bold uppercase font-mono hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:opacity-50 disabled:shadow-none whitespace-nowrap"
                >
                  {isAddingBulk ? <Loader2 className="animate-spin w-5 h-5 inline-block" /> : `Thêm vào Bài thi (${selectedGlobalQuestionIds.length})`}
                </button>
              </div>

              {isLoadingGlobal ? (
                <div className="flex justify-center items-center py-20"><Loader2 className="animate-spin text-black w-8 h-8" /></div>
              ) : availableGlobalQuestions.length === 0 ? (
                <div className="p-16 border-4 border-dashed border-black text-center bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
                  <p className="font-bold uppercase font-mono tracking-widest text-lg text-black mb-4">No available questions found.</p>
                  <p className="font-mono text-sm font-bold">Create a new question in this exam or choose another Topic filter.</p>
                </div>
              ) : (
                <div className="space-y-6" data-testid="question-bank-list">
                  {availableGlobalQuestions.map((q) => (
                    <div key={q.id} data-testid={`question-bank-item-${q.id}`} className="border-4 border-black p-6 bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex gap-4 items-start">
                      <div className="pt-1">
                        <input 
                          type="checkbox"
                          aria-label={`Select question: ${q.content}`}
                          checked={selectedGlobalQuestionIds.includes(q.id)}
                          onChange={() => toggleGlobalQuestionSelect(q.id)}
                          className="w-6 h-6 border-4 border-black accent-black cursor-pointer"
                        />
                      </div>
                      <div className="flex-1">
                        <div className="flex gap-3 mb-4 flex-wrap">
                          <span className="border-2 border-black px-3 py-1 text-sm font-bold uppercase font-mono bg-white">{q.points} ĐIỂM</span>
                          <span className="border-2 border-black px-3 py-1 text-sm font-bold uppercase font-mono bg-white">{q.question_type?.replace(/_/g, " ")}</span>
                        </div>
                        <h3 className="text-xl font-bold whitespace-pre-wrap">{q.content}</h3>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!isLoadingGlobal && globalPagination && globalPagination.pages > 1 && (
                <div className="mt-8 flex justify-center gap-6 items-center font-mono">
                  <button 
                    disabled={globalPage <= 1} 
                    onClick={() => setGlobalPage((p) => p - 1)}
                    className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors px-6 py-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold disabled:opacity-50 uppercase tracking-widest"
                  >
                    Prev
                  </button>
                  <span className="text-lg font-bold border-2 border-black px-4 py-2 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
                    {globalPage} / {globalPagination.pages}
                  </span>
                  <button 
                    disabled={globalPage >= globalPagination.pages} 
                    onClick={() => setGlobalPage((p) => p + 1)}
                    className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors px-6 py-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold disabled:opacity-50 uppercase tracking-widest"
                  >
                    Next
                  </button>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Form Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white border-4 border-black w-full max-w-4xl max-h-[90vh] flex flex-col shadow-[16px_16px_0px_0px_rgba(0,0,0,1)]">
            <div className="flex justify-between items-center p-6 border-b-4 border-black">
              <h2 className="text-2xl font-bold uppercase tracking-widest font-mono">
                {editingQuestionId ? "Sửa Câu hỏi" : "Thêm Câu hỏi mới"}
              </h2>
              <button onClick={handleCloseModal} className="p-2 hover:bg-black hover:text-white border-4 border-black bg-white transition-colors">
                <X size={24} />
              </button>
            </div>
            
            <div className="p-8 overflow-y-auto flex-1 space-y-8">
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono">Nội dung câu hỏi</label>
                  {questionType === "FILL_IN_BLANK" && (
                    <button
                      type="button"
                      onClick={handleInsertBlank}
                      className="text-xs font-bold uppercase tracking-widest font-mono border-4 border-black bg-black text-white px-4 py-2 hover:bg-white hover:text-black transition-colors flex items-center gap-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] active:shadow-none active:translate-x-[4px] active:translate-y-[4px]"
                      title="Bôi đen chữ và bấm để tự động tạo [BLANK] + Đáp án"
                    >
                      <Plus size={16} /> Chèn [BLANK]
                    </button>
                  )}
                </div>
                <textarea
                  data-testid="question-content-input"
                  id="exam_question_content_textarea"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full border-4 border-black p-4 min-h-[120px] focus:outline-none focus:ring-4 focus:ring-black/20 font-mono text-base resize-y"
                  placeholder="Nhập nội dung..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-3">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono">Loại</label>
                  <select
                    data-testid="question-type-select"
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value as QuestionType)}
                    className="w-full border-4 border-black p-4 focus:outline-none focus:ring-4 focus:ring-black/20 uppercase font-mono text-sm font-bold bg-white"
                  >
                    <option value="SINGLE_CHOICE">MỘT LỰA CHỌN</option>
                    <option value="MULTIPLE_CHOICE">NHIỀU LỰA CHỌN</option>
                    <option value="FILL_IN_BLANK">ĐIỀN KHUYẾT</option>
                    <option value="MATCHING">NỐI ĐÁP ÁN</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono">Độ khó</label>
                  <select
                    data-testid="exam-question-difficulty-select"
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as DifficultyLevel)}
                    className="w-full border-4 border-black p-4 focus:outline-none focus:ring-4 focus:ring-black/20 uppercase font-mono text-sm font-bold bg-white"
                  >
                    <option value="EASY">DỄ</option>
                    <option value="MEDIUM">TRUNG BÌNH</option>
                    <option value="HARD">KHÓ</option>
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="block text-sm font-bold uppercase tracking-widest font-mono">Điểm số</label>
                  <input
                    data-testid="question-points-input"
                    type="number"
                    min="1"
                    value={points}
                    onChange={(e) => setPoints(Number(e.target.value))}
                    className="w-full border-4 border-black p-4 focus:outline-none focus:ring-4 focus:ring-black/20 font-mono font-bold"
                  />
                </div>
              </div>

              <div className="space-y-6 pt-8 border-t-4 border-black">
                {questionType === "MATCHING" ? (
                  <MatchingBuilder pairs={matchingPairs} onChange={setMatchingPairs} />
                ) : questionType === "FILL_IN_BLANK" ? (
                  <FillInBlankBuilder content={content} blanks={fillInBlanks} onChange={setFillInBlanks} />
                ) : (
                  <>
                    <div className="flex justify-between items-center">
                      <label className="block text-sm font-bold uppercase tracking-widest font-mono">Đáp án</label>
                      <button
                        data-testid="add-option-button"
                        onClick={handleAddOption}
                        className="text-sm font-bold uppercase tracking-widest font-mono border-4 border-black bg-white px-4 py-2 hover:bg-black hover:text-white transition-colors flex items-center gap-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] active:shadow-none active:translate-x-[4px] active:translate-y-[4px]"
                      >
                        <Plus size={16} /> Thêm Đáp án
                      </button>
                    </div>
                    
                    <div className="space-y-4">
                      {options.map((opt, i) => (
                        <div key={i} className={`flex items-start gap-4 p-4 border-4 ${opt.is_correct ? 'border-black bg-gray-50' : 'border-dashed border-black bg-white'}`}>
                          <span className="font-bold font-mono text-xl mt-1 w-8">{String.fromCharCode(65 + i)}.</span>
                          <input
                            data-testid="option-content-input"
                            type="text"
                            value={opt.content}
                            onChange={(e) => handleOptionChange(i, "content", e.target.value)}
                            className="flex-1 border-4 border-black p-3 focus:outline-none focus:ring-4 focus:ring-black/20 font-mono text-base"
                            placeholder="Nội dung đáp án..."
                          />
                          <label className="flex items-center gap-3 mt-3 cursor-pointer select-none">
                            <input
                              data-testid="option-correct-checkbox"
                              type={questionType === "SINGLE_CHOICE" || questionType === "single_choice" || questionType === "true_false" ? "radio" : "checkbox"}
                              name={`correct_option_${editingQuestionId || 'new'}`}
                              checked={opt.is_correct}
                              onChange={(e) => handleOptionChange(i, "is_correct", e.target.checked)}
                              className="w-6 h-6 accent-black cursor-pointer border-4 border-black"
                            />
                            <span className="text-sm font-bold uppercase tracking-widest font-mono">Đúng</span>
                          </label>
                          <button
                            onClick={() => handleRemoveOption(i)}
                            className="mt-2 p-2 border-4 border-black hover:bg-black hover:text-white transition-colors bg-white"
                            title="Xóa"
                          >
                            <Trash2 size={20} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="p-6 border-t-4 border-black flex justify-end gap-6 bg-white">
              <button
                onClick={handleCloseModal}
                disabled={isSaving}
                className="px-8 py-3 border-4 border-black bg-white font-bold uppercase tracking-widest font-mono hover:bg-gray-100 transition-colors disabled:opacity-50"
              >
                Hủy
              </button>
              <button
                data-testid="save-question-button"
                onClick={handleSave}
                disabled={isSaving}
                className="px-8 py-3 border-4 border-black bg-black text-white font-bold uppercase tracking-widest font-mono hover:bg-white hover:text-black transition-colors disabled:opacity-50 flex items-center gap-3 shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px]"
              >
                {isSaving && <Loader2 className="animate-spin" size={20} />}
                {editingQuestionId ? "Lưu thay đổi" : "Tạo câu hỏi"}
              </button>
            </div>
          </div>
        </div>
      )}
      <ConfirmDialog />
    </div>
  );
}
