"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTopicDetail, updateTopic } from "@/hooks/useTopics";
import { 
  useTopicDecks, 
  updateTopicBrief, 
  generateTopicKitAi, 
  createDeck 
} from "@/hooks/useFlashcards";
import { useExams } from "@/hooks/useExams";
import { useMaterials } from "@/hooks/useMaterials";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Loader2, Plus, ArrowLeft, Wand2 } from "lucide-react";

export default function TopicDetailPage() {
  const params = useParams();
  const topicId = params.id as string;

  const { topic, isLoading, isError, mutate: mutateTopic } = useTopicDetail(topicId);
  const { decks, isLoading: isLoadingDecks, mutate: mutateDecks } = useTopicDecks(topicId);
  const { exams, isLoading: isLoadingExams } = useExams({ topic_id: topicId });
  const { materials, mutate: mutateMaterials } = useMaterials();

  if (isLoading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin w-8 h-8" /></div>;
  if (isError || !topic) return <div className="p-8">Error loading topic.</div>;

  return (
    <TopicEditor 
      topic={topic} 
      topicId={topicId} 
      mutateTopic={mutateTopic} 
      decks={decks} 
      isLoadingDecks={isLoadingDecks} 
      mutateDecks={mutateDecks} 
      exams={exams}
      isLoadingExams={isLoadingExams}
      materials={materials} 
      mutateMaterials={mutateMaterials}
    />
  );
}

import type { Topic, FlashcardDeck, Material, Exam, PaginatedResponse } from "@/types";
import { KeyedMutator } from "swr";
import { toast } from "@/components/ui/toast";
import { useConfirm } from "@/hooks/useConfirm";
import {
  getBackendErrorMessage,
  getMaterialDeleteConfirmation,
  parseBackendError,
} from "@/lib/errors";
import { deleteMaterial } from "@/services/apiService";

interface TopicEditorProps {
  topic: Topic;
  topicId: string;
  mutateTopic: KeyedMutator<Topic>;
  decks: FlashcardDeck[];
  isLoadingDecks: boolean;
  mutateDecks: KeyedMutator<FlashcardDeck[]>;
  exams: Exam[];
  isLoadingExams: boolean;
  materials: Material[];
  mutateMaterials: KeyedMutator<PaginatedResponse<Material>>;
}

function TopicEditor({ topic, topicId, mutateTopic, decks, isLoadingDecks, mutateDecks, exams, isLoadingExams, materials, mutateMaterials }: TopicEditorProps) {
  const router = useRouter();
  
  // Settings state
  const { confirm, ConfirmDialog } = useConfirm();
  const [settingsForm, setSettingsForm] = useState({ name: topic.name, description: topic.description || "" });
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // Topic Brief state
  const [briefContent, setBriefContent] = useState(topic.brief_content || "");
  const [isSavingBrief, setIsSavingBrief] = useState(false);
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [selectedMaterialId, setSelectedMaterialId] = useState("");

  // Flashcards state
  const [isDeckModalOpen, setIsDeckModalOpen] = useState(false);
  const [deckForm, setDeckForm] = useState({ title: "", description: "" });
  const [isCreatingDeck, setIsCreatingDeck] = useState(false);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingSettings(true);
    try {
      await updateTopic(topicId, settingsForm);
      mutateTopic();
      toast.add({ title: "Thông báo", description: "Settings saved successfully.", type: "info" });
    } catch {
      toast.add({ title: "Thông báo", description: "Failed to save settings.", type: "error" });
    } finally {
      setIsSavingSettings(false);
    }
  };

  const handleSaveBrief = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingBrief(true);
    try {
      await updateTopicBrief(topicId, { brief_content: briefContent });
      mutateTopic();
      toast.add({ title: "Thông báo", description: "Topic brief saved successfully.", type: "info" });
    } catch {
      toast.add({ title: "Thông báo", description: "Failed to save topic brief.", type: "error" });
    } finally {
      setIsSavingBrief(false);
    }
  };

  const handleGenerateAi = async () => {
    if (!selectedMaterialId) {
      toast.add({ title: "Thông báo", description: "Please select a material first.", type: "info" });
      return;
    }
    setIsGeneratingAi(true);
    try {
      await generateTopicKitAi(selectedMaterialId, topicId);
      mutateTopic();
      mutateDecks();
      toast.add({ title: "Thông báo", description: "AI Generation completed successfully.", type: "info" });
    } catch {
      toast.add({ title: "Thông báo", description: "Failed to generate with AI.", type: "error" });
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handleCreateDeck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deckForm.title) return;
    setIsCreatingDeck(true);
    try {
      await createDeck({ topic_id: topicId, ...deckForm });
      mutateDecks();
      setIsDeckModalOpen(false);
      setDeckForm({ title: "", description: "" });
    } catch {
      toast.add({ title: "Thông báo", description: "Failed to create deck.", type: "error" });
    } finally {
      setIsCreatingDeck(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto bg-white min-h-screen text-black space-y-8 font-mono">
      <header className="mb-8 flex flex-col gap-4 border-b-4 border-black pb-4">
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={() => router.push("/topics")} className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-black hover:text-white font-bold h-10 w-10 p-0">
            <ArrowLeft className="w-5 h-5 stroke-[3]" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold uppercase tracking-tight">Manage Topic: {topic.name}</h1>
          </div>
        </div>
      </header>

      <Tabs defaultValue="settings" className="w-full">
        <TabsList className="bg-transparent border-b-4 border-black w-full justify-start rounded-none h-auto p-0 mb-8 flex-wrap gap-4">
          <TabsTrigger value="settings" className="rounded-none border-4 border-black bg-white data-[state=active]:bg-black data-[state=active]:text-white data-[state=active]:shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black font-bold uppercase px-6 py-3 mb-2 translate-y-[2px]">Settings</TabsTrigger>
          <TabsTrigger value="materials" className="rounded-none border-4 border-black bg-white data-[state=active]:bg-black data-[state=active]:text-white data-[state=active]:shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black font-bold uppercase px-6 py-3 mb-2 translate-y-[2px]">Materials</TabsTrigger>
          <TabsTrigger value="brief" className="rounded-none border-4 border-black bg-white data-[state=active]:bg-black data-[state=active]:text-white data-[state=active]:shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black font-bold uppercase px-6 py-3 mb-2 translate-y-[2px]">Topic Brief</TabsTrigger>
          <TabsTrigger value="flashcards" className="rounded-none border-4 border-black bg-white data-[state=active]:bg-black data-[state=active]:text-white data-[state=active]:shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black font-bold uppercase px-6 py-3 mb-2 translate-y-[2px]">Flashcards</TabsTrigger>
          <TabsTrigger value="exams" className="rounded-none border-4 border-black bg-white data-[state=active]:bg-black data-[state=active]:text-white data-[state=active]:shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black font-bold uppercase px-6 py-3 mb-2 translate-y-[2px]">Exams</TabsTrigger>
          <TabsTrigger value="questions" className="rounded-none border-4 border-black bg-white data-[state=active]:bg-black data-[state=active]:text-white data-[state=active]:shadow-[4px_4px_0_0_rgba(0,0,0,1)] text-black font-bold uppercase px-6 py-3 mb-2 translate-y-[2px]">Questions</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <h2 className="text-xl font-bold mb-4 uppercase">Topic Settings</h2>
          <form onSubmit={handleSaveSettings} className="space-y-6">
            <div>
              <label className="block text-sm font-bold mb-2 uppercase">Name</label>
              <Input 
                value={settingsForm.name}
                onChange={(e) => setSettingsForm({ ...settingsForm, name: e.target.value })}
                className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] focus:ring-0 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-bold mb-2 uppercase">Description</label>
              <textarea 
                value={settingsForm.description}
                onChange={(e) => setSettingsForm({ ...settingsForm, description: e.target.value })}
                className="w-full border-4 border-black p-3 min-h-[120px] shadow-[4px_4px_0_0_rgba(0,0,0,1)] outline-none focus:ring-0 resize-none"
              />
            </div>
            <Button type="submit" disabled={isSavingSettings} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase px-8">
              {isSavingSettings && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Save Settings
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="materials" className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold uppercase">Topic Materials</h2>
            <Button onClick={() => router.push("/ai-workspace")} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase">
              <Plus className="w-4 h-4 mr-2 stroke-[3]" /> Upload Material
            </Button>
          </div>
          {materials.length === 0 ? (
            <div className="text-center p-8 border-4 border-black border-dashed">
              <p className="font-bold">No materials found.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {materials.map(m => (
                <div key={m.id} className="border-4 border-black p-4 bg-white flex justify-between items-center shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
                  <div>
                    <h3 className="font-bold text-lg">{m.title}</h3>
                    <p className="text-sm font-mono text-gray-600">Status: {m.ai_status.toUpperCase()}</p>
                  </div>
                  <Button 
                    variant="outline" 
                    onClick={async () => {
                      try {
                        await deleteMaterial(m.id);
                        toast.add({
                          title: "Material deleted",
                          description: "The material was deleted.",
                          type: "info",
                        });
                        mutateMaterials();
                      } catch (error) {
                        const backendError = parseBackendError(error);
                        if (
                          backendError?.error_code ===
                          "MATERIAL_DELETE_REQUIRES_CASCADE"
                        ) {
                          const prompt = getMaterialDeleteConfirmation(error);
                          if (!(await confirm(prompt))) return;
                          try {
                            await deleteMaterial(m.id, true);
                            toast.add({
                              title: "Material deleted",
                              description:
                                "The material and linked resources were deleted.",
                              type: "info",
                            });
                            mutateMaterials();
                            return;
                          } catch (cascadeError) {
                            toast.add({
                              title: "Delete failed",
                              description: getBackendErrorMessage(
                                cascadeError,
                                "The material could not be deleted.",
                              ),
                              type: "error",
                            });
                            return;
                          }
                        }
                        toast.add({
                          title: "Delete failed",
                          description: getBackendErrorMessage(
                            error,
                            "The material could not be deleted.",
                          ),
                          type: "error",
                        });
                      }
                    }}
                    className="border-2 border-black rounded-none h-10 bg-white hover:bg-black hover:text-white transition-colors text-black font-bold uppercase"
                  >
                    Delete
                  </Button>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="brief" className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
            <h2 className="text-xl font-bold uppercase">Topic Brief (Markdown)</h2>
            <div className="flex flex-col md:flex-row items-center gap-2 w-full md:w-auto">
              <select
                value={selectedMaterialId}
                onChange={(e) => setSelectedMaterialId(e.target.value)}
                className="border-4 border-black p-2 rounded-none font-bold outline-none focus:ring-0 w-full md:w-48 bg-white"
              >
                <option value="">-- SELECT MATERIAL --</option>
                {materials.map(m => (
                  <option key={m.id} value={m.id}>{m.title}</option>
                ))}
              </select>
              <Button 
                onClick={handleGenerateAi} 
                disabled={isGeneratingAi || !selectedMaterialId} 
                className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase shrink-0 w-full md:w-auto"
              >
                {isGeneratingAi ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
                Tạo Tự Động Bằng AI
              </Button>
            </div>
          </div>
          <form onSubmit={handleSaveBrief} className="space-y-6">
            <div>
              <textarea 
                value={briefContent}
                onChange={(e) => setBriefContent(e.target.value)}
                className="w-full border-4 border-black p-4 min-h-[300px] shadow-[4px_4px_0_0_rgba(0,0,0,1)] outline-none focus:ring-0 resize-y font-mono"
                placeholder="# Enter topic content in Markdown..."
              />
            </div>
            <Button type="submit" disabled={isSavingBrief} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase px-8">
              {isSavingBrief && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Save Brief
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="flashcards" className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold uppercase">Flashcard Decks</h2>
            <Button onClick={() => setIsDeckModalOpen(true)} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase">
              <Plus className="w-4 h-4 mr-2 stroke-[3]" /> Create Deck
            </Button>
          </div>

          {isLoadingDecks ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin w-8 h-8" /></div>
          ) : decks.length === 0 ? (
            <div className="text-center p-8 border-4 border-black border-dashed">
              <p className="font-bold">No flashcard decks found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {decks.map(deck => (
                <div key={deck.id} className="border-4 border-black p-4 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] flex flex-col">
                  <h3 className="font-bold text-lg uppercase truncate mb-2">{deck.title}</h3>
                  <p className="text-sm flex-1 mb-4">{deck.description || "No description"}</p>
                  <Button variant="outline" className="border-2 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] font-bold uppercase w-full">
                    Manage Cards
                  </Button>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="exams" className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold uppercase">Topic Exams</h2>
            <Button onClick={() => router.push(`/exams?topic_id=${topicId}&create=1`)} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase">
              <Plus className="w-4 h-4 mr-2 stroke-[3]" /> Create Exam
            </Button>
          </div>

          {isLoadingExams ? (
            <div className="flex justify-center p-8"><Loader2 className="animate-spin w-8 h-8" /></div>
          ) : exams.length === 0 ? (
            <div className="text-center p-8 border-4 border-black border-dashed">
              <p className="font-bold">No exams found for this topic.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {exams.map(exam => (
                <div key={exam.id} className="border-4 border-black p-4 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] flex flex-col">
                  <h3 className="font-bold text-lg uppercase truncate mb-2">{exam.title}</h3>
                  <p className="text-sm flex-1 mb-4">{exam.description || "No description"}</p>
                  <p className="text-sm font-bold mb-4 font-mono border-2 border-black p-2 text-center bg-gray-100">{exam.duration_minutes} mins</p>
                  <Button variant="outline" onClick={() => router.push(`/exams/${exam.id}`)} className="border-2 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] font-bold uppercase w-full">
                    Manage Exam
                  </Button>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="questions" className="border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold uppercase">Topic Questions Bank</h2>
            <Button onClick={() => router.push("/questions")} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase">
              Go to Global Question Bank
            </Button>
          </div>
          <div className="text-center p-8 border-4 border-black border-dashed">
            <p className="font-bold">Quản lý câu hỏi đang được phát triển...</p>
            <p className="text-sm mt-2">Tính năng này sẽ cho phép duyệt và sửa câu hỏi thuộc Topic này.</p>
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={isDeckModalOpen} onOpenChange={setIsDeckModalOpen}>
        <DialogContent className="border-4 border-black rounded-none bg-white shadow-[12px_12px_0_0_rgba(0,0,0,1)] p-0 sm:max-w-md font-mono">
          <DialogHeader className="p-6 border-b-4 border-black">
            <DialogTitle className="text-2xl font-bold uppercase text-black">Create Deck</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateDeck} className="p-6 space-y-6">
            <div>
              <label className="block text-sm font-bold mb-2 uppercase text-black">Title</label>
              <Input 
                value={deckForm.title}
                onChange={(e) => setDeckForm({ ...deckForm, title: e.target.value })}
                className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] focus:ring-0 focus:outline-none text-black bg-white"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-bold mb-2 uppercase text-black">Description</label>
              <textarea 
                value={deckForm.description}
                onChange={(e) => setDeckForm({ ...deckForm, description: e.target.value })}
                className="w-full border-4 border-black p-3 min-h-[100px] shadow-[4px_4px_0_0_rgba(0,0,0,1)] outline-none focus:ring-0 resize-none text-black bg-white"
              />
            </div>
            <DialogFooter className="gap-4 sm:justify-start">
              <Button type="button" variant="outline" onClick={() => setIsDeckModalOpen(false)} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase flex-1">
                Cancel
              </Button>
              <Button type="submit" disabled={isCreatingDeck} className="border-4 border-black rounded-none bg-white text-black hover:bg-black hover:text-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-bold uppercase flex-1">
                {isCreatingDeck && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Create
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog />
    </div>
  );
}
