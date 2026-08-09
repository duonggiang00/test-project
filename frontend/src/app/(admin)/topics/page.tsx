"use client";

import { useState } from "react";
import Link from "next/link";
import { useTopics, createTopic, updateTopic, deleteTopic } from "@/hooks/useTopics";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Loader2, Plus, Edit, Trash2 } from "lucide-react";
import { Topic } from "@/types";
import { toast } from "@/components/ui/toast";
import { useConfirm } from "@/hooks/useConfirm";
import { logBackendError } from "@/lib/errors";

export default function TopicsPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTopic, setEditingTopic] = useState<Topic | null>(null);
  const [formData, setFormData] = useState({ name: "", description: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { confirm, ConfirmDialog } = useConfirm();

  // Apply debounce manually or just use standard search for now (we can do basic on blur or form submit for simplicity, or just a simple hook).
  // For wireframe minimalism, let's keep it simple: press Enter to search, or just search as you type.
  const { topics, pagination, isLoading, isError, mutate } = useTopics({ page, size: 10, search: debouncedSearch });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setDebouncedSearch(search);
    setPage(1);
  };

  const openModal = (topic?: Topic) => {
    if (topic) {
      setEditingTopic(topic);
      setFormData({ name: topic.name, description: topic.description || "" });
    } else {
      setEditingTopic(null);
      setFormData({ name: "", description: "" });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingTopic(null);
    setFormData({ name: "", description: "" });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) return;
    setIsSubmitting(true);
    try {
      if (editingTopic) {
        await updateTopic(editingTopic.id, formData);
      } else {
        await createTopic(formData);
      }
      mutate();
      closeModal();
    } catch (error) {
      logBackendError("Topic save failed", error);
      toast.add({ title: "Thông báo", description: "An error occurred", type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (await confirm("Are you sure you want to delete this topic?")) {
      try {
        await deleteTopic(id);
        mutate();
      } catch (error) {
        logBackendError("Topic delete failed", error);
        toast.add({ title: "Thông báo", description: "Failed to delete topic", type: "error" });
      }
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto bg-white min-h-screen text-black space-y-8">
      <header className="mb-8 flex flex-col md:flex-row md:justify-between md:items-end gap-4 border-b-4 border-black pb-4">
        <div>
          <h1 className="text-3xl font-bold uppercase tracking-tight mb-2">Topics Management</h1>
          <p className="text-black font-mono">Quản lý các chủ đề và danh mục.</p>
        </div>
        <Button data-testid="add-topic-button" onClick={() => openModal()} className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono font-bold">
          <Plus className="w-5 h-5 mr-2 stroke-[3]" />
          ADD TOPIC
        </Button>
      </header>

      <section className="border-4 border-black p-4 mb-8 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-black font-bold">search</span>
            <Input 
              data-testid="search-topic-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search topics..."
              className="pl-10 border-4 border-black rounded-none bg-white focus:ring-0 focus:outline-none font-mono shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black"
            />
          </div>
          <Button data-testid="search-topic-button" type="submit" className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono font-bold">
            SEARCH
          </Button>
        </form>
      </section>

      <section className="border-4 border-black bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)] overflow-x-auto">
        <Table className="w-full">
          <TableHeader className="bg-white">
            <TableRow className="border-b-4 border-black hover:bg-transparent">
              <TableHead className="font-bold text-black uppercase border-r-4 border-black h-12 px-4">Name</TableHead>
              <TableHead className="font-bold text-black uppercase border-r-4 border-black h-12 px-4">Description</TableHead>
              <TableHead className="font-bold text-black uppercase w-[150px] text-right h-12 px-4">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="font-mono text-black divide-y-4 divide-black">
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-10">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto stroke-[3]" />
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-10 text-black font-bold">
                  Error loading topics.
                </TableCell>
              </TableRow>
            ) : topics.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-10 text-black font-bold">
                  No topics found.
                </TableCell>
              </TableRow>
            ) : (
              topics.map((topic) => (
                <TableRow key={topic.id} className="border-b-4 border-black hover:bg-gray-100 transition-colors">
                  <TableCell className="font-bold border-r-4 border-black p-4">{topic.name}</TableCell>
                  <TableCell className="border-r-4 border-black p-4">{topic.description || <span className="text-black italic">No description</span>}</TableCell>
                  <TableCell className="p-4">
                    <div className="flex gap-2 justify-end">
                      <Button data-testid="edit-topic-button" variant="outline" size="icon" onClick={() => openModal(topic)} className="border-2 border-black rounded-none h-10 w-10 bg-white hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black">
                        <Edit className="w-5 h-5 stroke-[2]" />
                      </Button>
                      <Button data-testid="delete-topic-button" variant="outline" size="icon" onClick={() => handleDelete(topic.id)} className="border-2 border-black rounded-none h-10 w-10 bg-white hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black">
                        <Trash2 className="w-5 h-5 stroke-[2]" />
                      </Button>
                      <Link href={`/topics/${topic.id}`}>
                        <Button data-testid="manage-topic-button" className="border-2 border-black rounded-none h-10 bg-white hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black font-bold uppercase">
                          Manage
                        </Button>
                      </Link>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </section>

      {!isLoading && !isError && pagination && pagination.pages > 1 && (
        <div className="mt-8 flex justify-center gap-6 items-center font-mono">
          <Button 
            disabled={page <= 1} 
            onClick={() => setPage((p) => p - 1)}
            className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold disabled:opacity-50"
          >
            PREV
          </Button>
          <span className="text-lg font-bold border-2 border-black px-4 py-2 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
            {page} / {pagination.pages}
          </span>
          <Button 
            disabled={page >= pagination.pages} 
            onClick={() => setPage((p) => p + 1)}
            className="border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold disabled:opacity-50"
          >
            NEXT
          </Button>
        </div>
      )}

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="border-4 border-black rounded-none bg-white shadow-[12px_12px_0_0_rgba(0,0,0,1)] p-0 sm:max-w-lg">
          <DialogHeader className="p-6 border-b-4 border-black bg-white">
            <DialogTitle className="text-2xl font-bold uppercase tracking-tight text-black">{editingTopic ? "EDIT TOPIC" : "ADD TOPIC"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-6 p-6 font-mono bg-white">
            <div>
              <label className="block text-sm font-bold mb-2 uppercase text-black">Name</label>
              <Input 
                data-testid="topic-name-input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="TOPIC NAME"
                required
                className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] focus:ring-0 focus:outline-none text-black bg-white"
              />
            </div>
            <div>
              <label className="block text-sm font-bold mb-2 uppercase text-black">Description</label>
              <textarea 
                data-testid="topic-description-input"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="TOPIC DESCRIPTION"
                className="w-full border-4 border-black p-3 min-h-[120px] shadow-[4px_4px_0_0_rgba(0,0,0,1)] outline-none focus:ring-0 text-black resize-none bg-white"
              />
            </div>
            <DialogFooter className="mt-4 gap-4 flex-col sm:flex-row">
              <Button type="button" variant="outline" onClick={closeModal} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase w-full sm:w-auto">
                CANCEL
              </Button>
              <Button data-testid="save-topic-button" type="submit" disabled={isSubmitting} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase w-full sm:w-auto">
                {isSubmitting && <Loader2 className="w-5 h-5 mr-2 animate-spin stroke-[3]" />}
                {editingTopic ? "SAVE CHANGES" : "CREATE TOPIC"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog />
    </div>
  );
}
