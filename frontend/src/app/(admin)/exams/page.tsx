"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Plus, Edit, Trash, FileText } from "lucide-react";
import { useExams, createExam, updateExam, deleteExam } from "@/hooks/useExams";
import type { Exam } from "@/types";
import { useTopics } from "@/hooks/useTopics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { logBackendError } from "@/lib/errors";

function ExamsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedTopicId = searchParams.get("topic_id") || "";
  const createIntentKey = searchParams.get("create") === "1"
    ? `${requestedTopicId}:create`
    : null;
  const [dismissedCreateIntent, setDismissedCreateIntent] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [topicId, setTopicId] = useState(requestedTopicId);

  const { exams, pagination, isLoading, mutate } = useExams({
    page,
    size: 10,
    search,
    topic_id: topicId || undefined,
  });

  const { topics } = useTopics({ size: 100 });

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingExamId, setEditingExamId] = useState<string | null>(null);
  const [deletingExamId, setDeletingExamId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    duration_minutes: 45,
    is_published: false,
    topic_id: requestedTopicId,
  });

  const shouldOpenFromQuery = createIntentKey !== null
    && dismissedCreateIntent !== createIntentKey;

  const clearCreateIntent = () => {
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.delete("create");
    const nextQuery = nextParams.toString();
    router.replace(nextQuery ? `/exams?${nextQuery}` : "/exams");
  };

  const handleModalOpenChange = (open: boolean) => {
    setIsModalOpen(open);
    if (!open && shouldOpenFromQuery) {
      setDismissedCreateIntent(createIntentKey);
      clearCreateIntent();
    }
  };

  const handleOpenCreate = () => {
    setEditingExamId(null);
    setFormData({
      title: "",
      description: "",
      duration_minutes: 45,
      is_published: false,
      topic_id: topicId,
    });
    setIsModalOpen(true);
  };

  const handleOpenEdit = (exam: Exam) => {
    setEditingExamId(exam.id);
    setFormData({
      title: exam.title,
      description: exam.description || "",
      duration_minutes: exam.duration_minutes,
      is_published: exam.is_published,
      topic_id: exam.topic_id || "",
    });
    setIsModalOpen(true);
  };

  const handleDelete = (id: string) => {
    setDeletingExamId(id);
  };

  const confirmDelete = async (id: string) => {
    setIsDeleting(true);
    try {
      await deleteExam(id);
      toast.add({ title: "Exam deleted", description: "The exam was deleted.", type: "success" });
      mutate();
    } catch (error) {
      logBackendError("Exam delete failed", error);
      toast.add({ title: "Delete failed", description: "The exam could not be deleted.", type: "error" });
    } finally {
      setIsDeleting(false);
      setDeletingExamId(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        ...formData,
        is_published: editingExamId ? formData.is_published : false,
        topic_id: formData.topic_id ? formData.topic_id : null,
      };

      if (editingExamId) {
        await updateExam(editingExamId, payload);
        setIsModalOpen(false);
        toast.add({ title: "Success", description: "Exam updated.", type: "success" });
        await mutate();
      } else {
        const createdExam = await createExam(payload);
        toast.add({ title: "Draft created", description: "Add questions before publishing.", type: "success" });
        router.push(`/exams/${createdExam.id}`);
      }
    } catch (error) {
      logBackendError("Exam save failed", error);
      toast.add({ title: "Save failed", description: "The exam could not be saved.", type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto bg-white text-black min-h-screen">
      <div className="flex items-center justify-between mb-8 border-b-4 border-black pb-6">
        <h1 className="text-3xl font-bold uppercase tracking-widest font-mono">Exam Management</h1>
        <Button
          data-testid="add-exam-button"
          onClick={handleOpenCreate}
          className="border-4 border-black bg-black text-white font-bold uppercase font-mono tracking-widest hover:bg-white hover:text-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px]"
        >
          <Plus className="w-5 h-5 mr-2" />
          Add Exam
        </Button>
      </div>

      <div className="flex gap-4 mb-8">
        <Input
          data-testid="search-exam-input"
          placeholder="Search exams..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-4 focus:ring-black/20 rounded-none w-80 text-base"
        />
        <select
          data-testid="filter-topic-select"
          value={topicId}
          onChange={(e) => setTopicId(e.target.value)}
          className="border-4 border-black p-3 bg-white text-black font-mono focus:outline-none focus:ring-4 focus:ring-black/20 rounded-none min-w-[200px] text-base font-bold uppercase"
        >
          <option value="">All Topics</option>
          {topics.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      <div className="border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] bg-white">
        <Table>
          <TableHeader>
            <TableRow className="border-b-4 border-black hover:bg-transparent bg-white">
              <TableHead className="text-black font-bold uppercase font-mono tracking-widest border-r-4 border-black">Title</TableHead>
              <TableHead className="text-black font-bold uppercase font-mono tracking-widest border-r-4 border-black">Topic</TableHead>
              <TableHead className="text-black font-bold uppercase font-mono tracking-widest border-r-4 border-black">Duration</TableHead>
              <TableHead className="text-black font-bold uppercase font-mono tracking-widest border-r-4 border-black">Status</TableHead>
              <TableHead className="text-black font-bold uppercase font-mono tracking-widest text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center p-12">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto text-black" />
                </TableCell>
              </TableRow>
            ) : exams.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center p-12 text-black font-mono font-bold uppercase tracking-widest border-dashed border-4 border-black m-4">
                  No exams found.
                </TableCell>
              </TableRow>
            ) : (
              exams.map((exam) => {
                const topicName = topics.find((t) => t.id === exam.topic_id)?.name || "-";
                return (
                  <TableRow key={exam.id} data-testid={`exam-row-${exam.title}`} className="border-b-4 border-black hover:bg-white transition-colors">
                    <TableCell className="border-r-4 border-black font-bold text-lg">{exam.title}</TableCell>
                    <TableCell className="border-r-4 border-black font-mono">{topicName}</TableCell>
                    <TableCell className="border-r-4 border-black font-mono">{exam.duration_minutes} MINS</TableCell>
                    <TableCell className="border-r-4 border-black">
                      <span className={`inline-block px-2 py-1 font-bold text-xs uppercase font-mono border-2 border-black ${exam.is_published ? 'bg-black text-white' : 'bg-white text-black'}`}>
                        {exam.is_published ? "PUBLISHED" : "DRAFT"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Link href={`/exams/${exam.id}`}>
                          <Button data-testid="exam-builder-link" size="sm" variant="outline" className="border-2 border-black rounded-none bg-black text-white hover:bg-white hover:text-black font-mono font-bold uppercase">
                            <FileText className="w-4 h-4 mr-2" />
                            Builder
                          </Button>
                        </Link>
                        <Button
                          data-testid="edit-exam-button"
                          size="sm"
                          variant="outline"
                          onClick={() => handleOpenEdit(exam)}
                          className="border-2 border-black rounded-none bg-white hover:bg-black hover:text-white"
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          data-testid="delete-exam-button"
                          size="sm"
                          variant="outline"
                          onClick={() => handleDelete(exam.id)}
                          className="border-2 border-black rounded-none bg-white hover:bg-black hover:text-white"
                        >
                          <Trash className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between mt-8">
        <div className="text-base font-bold font-mono tracking-widest uppercase">
          Page {pagination.page} of {pagination.pages}
        </div>
        <div className="flex gap-4">
          <Button
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            variant="outline"
            className="border-4 border-black rounded-none font-bold uppercase font-mono shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] disabled:opacity-50 disabled:hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:hover:translate-x-0 disabled:hover:translate-y-0"
          >
            Previous
          </Button>
          <Button
            disabled={page >= pagination.pages}
            onClick={() => setPage((p) => p + 1)}
            variant="outline"
            className="border-4 border-black rounded-none font-bold uppercase font-mono shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] disabled:opacity-50 disabled:hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:hover:translate-x-0 disabled:hover:translate-y-0"
          >
            Next
          </Button>
        </div>
      </div>

      <Dialog open={isModalOpen || shouldOpenFromQuery} onOpenChange={handleModalOpenChange}>
        <DialogContent className="border-4 border-black bg-white rounded-none sm:max-w-[600px] text-black shadow-[16px_16px_0_0_rgba(0,0,0,1)] p-0 max-h-[90vh] overflow-y-auto">
          <DialogHeader className="p-6 border-b-4 border-black bg-white">
            <DialogTitle className="text-2xl font-bold uppercase tracking-widest font-mono text-black">
              {editingExamId ? "Edit Exam" : "Create Exam Draft"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="p-6 space-y-6 bg-white">
            <div className="space-y-3">
              <label className="block text-sm font-bold uppercase tracking-widest font-mono">Title</label>
              <Input
                data-testid="exam-title-input"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full border-4 border-black p-3 rounded-none font-mono text-base focus:outline-none focus:ring-4 focus:ring-black/20"
              />
            </div>
            
            <div className="space-y-3">
              <label className="block text-sm font-bold uppercase tracking-widest font-mono">Description</label>
              <Input
                data-testid="exam-description-input"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full border-4 border-black p-3 rounded-none font-mono text-base focus:outline-none focus:ring-4 focus:ring-black/20"
              />
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-bold uppercase tracking-widest font-mono">Topic</label>
              <select
                data-testid="exam-topic-select"
                value={formData.topic_id}
                onChange={(e) => setFormData({ ...formData, topic_id: e.target.value })}
                className="w-full border-4 border-black p-3 bg-white text-black rounded-none font-mono text-base font-bold uppercase focus:outline-none focus:ring-4 focus:ring-black/20"
              >
                <option value="">NO TOPIC</option>
                {topics.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-bold uppercase tracking-widest font-mono">Duration (Minutes)</label>
              <Input
                data-testid="exam-duration-input"
                type="number"
                min={1}
                required
                value={formData.duration_minutes}
                onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
                className="w-full border-4 border-black p-3 rounded-none font-mono text-base focus:outline-none focus:ring-4 focus:ring-black/20 font-bold"
              />
            </div>

            {editingExamId ? (
              <label className="flex items-center gap-3 pt-2 cursor-pointer select-none">
                <input
                  data-testid="exam-published-checkbox"
                  type="checkbox"
                  checked={formData.is_published}
                  onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                  className="w-6 h-6 accent-black cursor-pointer border-4 border-black rounded-none"
                />
                <span className="font-bold text-sm uppercase tracking-widest font-mono">
                  Published
                </span>
              </label>
            ) : (
              <p className="border-4 border-dashed border-black p-4 font-mono text-sm font-bold uppercase">
                [DRAFT] Add and review questions before publishing this exam.
              </p>
            )}

            <div className="flex justify-end gap-4 pt-6 border-t-4 border-black mt-6">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleModalOpenChange(false)}
                className="px-8 py-3 border-4 border-black rounded-none font-bold uppercase tracking-widest font-mono bg-white hover:bg-white text-black"
              >
                Cancel
              </Button>
              <Button
                data-testid="save-exam-button"
                type="submit"
                disabled={isSubmitting}
                className="px-8 py-3 border-4 border-black rounded-none font-bold uppercase tracking-widest font-mono bg-black text-white hover:bg-white hover:text-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] disabled:opacity-50 disabled:hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:hover:translate-x-0 disabled:hover:translate-y-0"
              >
                {isSubmitting && <Loader2 className="w-5 h-5 mr-3 animate-spin" />}
                {editingExamId ? "Update" : "Create Draft"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deletingExamId} onOpenChange={(open) => !open && setDeletingExamId(null)}>
        <DialogContent className="border-4 border-black bg-white rounded-none sm:max-w-[400px] text-black shadow-[16px_16px_0_0_rgba(0,0,0,1)] p-0">
          <DialogHeader className="p-6 border-b-4 border-black bg-white">
            <DialogTitle className="text-2xl font-bold uppercase tracking-widest font-mono text-black">
              Delete exam
            </DialogTitle>
          </DialogHeader>
          <div className="p-6 bg-white">
            <p className="mb-8 font-bold font-mono text-lg">Are you sure you want to delete this exam?</p>
            <div className="flex justify-end gap-4 border-t-4 border-black pt-6">
              <Button
                variant="outline"
                onClick={() => setDeletingExamId(null)}
                className="px-6 py-2 border-4 border-black rounded-none font-bold uppercase tracking-widest font-mono bg-white hover:bg-white text-black"
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                data-testid="confirm-delete-exam-button"
                onClick={() => deletingExamId && confirmDelete(deletingExamId)}
                className="px-6 py-2 border-4 border-black rounded-none font-bold uppercase tracking-widest font-mono bg-black text-white hover:bg-white hover:text-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] disabled:opacity-50 disabled:hover:shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:hover:translate-x-0 disabled:hover:translate-y-0"
                disabled={isDeleting}
              >
                {isDeleting && <Loader2 className="w-5 h-5 mr-3 animate-spin" />}
                Delete
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ExamsPage() {
  return (
    <Suspense
      fallback={(
        <div className="min-h-screen bg-white p-8 text-black font-mono font-bold uppercase">
          Loading Exam Builder...
        </div>
      )}
    >
      <ExamsPageContent />
    </Suspense>
  );
}
