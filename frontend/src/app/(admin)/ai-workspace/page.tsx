"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { useUserStore } from "@/lib/store";
import GenerativePreview from "./GenerativePreview";
import { useMaterials } from "@/hooks/useMaterials";
import { useTopics } from "@/hooks/useTopics";
import type { Topic } from "@/types";
import {
  deleteMaterial,
  generateMaterialFlashcards,
  generateMaterialQuestions,
  generateMaterialTopicBrief,
  openAiChatStream,
  uploadMaterial,
} from "@/services/apiService";
import { toast } from "@/components/ui/toast";
import { getBackendErrorMessage, getErrorMessage } from "@/lib/errors";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export default function AIWorkspacePage() {
  const { materials, isLoading, mutate } = useMaterials(5000);
  const { topics } = useTopics({ size: 100 });
  const [selectedTopicId, setSelectedTopicId] = useState<string>("");
  const [activeMaterial, setActiveMaterial] = useState<string | null>(null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [questionCount, setQuestionCount] = useState(5);
  const [materialToDelete, setMaterialToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Xin chào! Chọn một tài liệu ở cột bên trái để AI tự động sinh câu hỏi và flashcard, hoặc trò chuyện trực tiếp tại đây." }
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeToolCall, setActiveToolCall] = useState<{name: string, args: string | Record<string, unknown>} | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useUserStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages, activeToolCall]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!selectedTopicId) {
       toast.add({ title: "Thông báo", description: "Vui lòng chọn chủ đề trước khi tải lên", type: "warning" });
       e.target.value = '';
       return;
    }

    setIsUploading(true);
    try {
      toast.add({
        title: "Đang tải lên...",
        description: "AI đang phân tích tài liệu (khoảng 30s).",
        type: "info"
      });
      await uploadMaterial(file, selectedTopicId);
      toast.add({
        title: "Thành công",
        description: "Tài liệu đã vào hàng đợi AI.",
        type: "success"
      });
      e.target.value = '';
      mutate();
    } catch (error) {
      toast.add({
        title: "Upload failed",
        description: getBackendErrorMessage(
          error,
          "The material could not be uploaded.",
        ),
        type: "error"
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteMaterial = async () => {
    if (!materialToDelete) return;
    setIsDeleting(true);
    try {
      await deleteMaterial(materialToDelete, false, true);
      toast.add({
        title: "Thành công",
        description: "Đã xóa tài liệu khỏi hệ thống.",
        type: "success"
      });
      if (activeMaterial === materialToDelete) {
        setActiveMaterial(null);
      }
      setMaterialToDelete(null);
      mutate();
    } catch (error) {
      toast.add({
        title: "Delete failed",
        description: getBackendErrorMessage(
          error,
          "The material could not be deleted.",
        ),
        type: "error"
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const generateQuestions = async () => {
    if (!activeMaterial) return;
    setIsStreaming(true);
    setActiveToolCall({ name: "draft_exam", args: "" });
    setMessages(prev => [...prev, { role: "assistant", content: "[...] Đang sinh câu hỏi từ tài liệu..." }]);
    
    try {
      const data = await generateMaterialQuestions(
        activeMaterial,
        questionCount,
      );
      setActiveToolCall({ name: "draft_exam", args: data });
      setMessages(prev => [...prev, { role: "assistant", content: "[OK] Đã sinh xong câu hỏi. Xem kết quả ở khu vực hiển thị bên dưới." }]);
    } catch (error) {
      toast.add({
        title: "Question generation failed",
        description: getBackendErrorMessage(
          error,
          "Questions could not be generated.",
        ),
        type: "error",
      });
      setActiveToolCall(null);
    } finally {
      setIsStreaming(false);
    }
  };

  const generateFlashcards = async () => {
    if (!activeMaterial) return;
    setIsStreaming(true);
    setActiveToolCall({ name: "draft_flashcards", args: "" });
    setMessages(prev => [...prev, { role: "assistant", content: "[...] Đang tạo flashcards từ tài liệu..." }]);
    
    try {
      const data = await generateMaterialFlashcards(
        activeMaterial,
        questionCount,
      );
      setActiveToolCall({ name: "draft_flashcards", args: data });
      setMessages(prev => [...prev, { role: "assistant", content: "[OK] Đã sinh xong flashcards. Xem kết quả ở khu vực hiển thị bên dưới." }]);
    } catch (error) {
      toast.add({
        title: "Flashcard generation failed",
        description: getBackendErrorMessage(
          error,
          "Flashcards could not be generated.",
        ),
        type: "error",
      });
      setActiveToolCall(null);
    } finally {
      setIsStreaming(false);
    }
  };

  const generateTopicBrief = async () => {
    if (!activeMaterial) return;
    setIsStreaming(true);
    setActiveToolCall({ name: "draft_topic_brief", args: "" });
    setMessages(prev => [...prev, { role: "assistant", content: "[...] Đang tóm tắt dàn ý tài liệu..." }]);
    
    try {
      const data = await generateMaterialTopicBrief(activeMaterial);
      setActiveToolCall({ name: "draft_topic_brief", args: data });
      setMessages(prev => [...prev, { role: "assistant", content: "[OK] Đã tạo xong dàn ý. Xem kết quả ở khu vực hiển thị bên dưới." }]);
    } catch (error) {
      toast.add({
        title: "Topic brief generation failed",
        description: getBackendErrorMessage(
          error,
          "The topic brief could not be generated.",
        ),
        type: "error",
      });
      setActiveToolCall(null);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming || !activeMaterial) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);

    try {
      const history = [...messages.filter(m => m.role !== "system" && m !== messages[0]), userMessage];
      const res = await openAiChatStream(history, activeMaterial);

      if (!res.ok) {
        const errorBody = await res.json().catch(() => ({}));
        const safeMessage = getBackendErrorMessage(
          errorBody,
          "The AI chat request could not be completed.",
        );
        setMessages(prev => [
          ...prev,
          { role: "assistant", content: `\n\n[ERROR] ${safeMessage}` },
        ]);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      if (reader) {
        setMessages(prev => [...prev, { role: "assistant", content: "" }]);
        setActiveToolCall(null);
        let buffer = "";
        let streamFailed = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";
          
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.replace("data: ", "").trim();
              if (dataStr === "[DONE]") continue;
              try {
                const data = JSON.parse(dataStr);
                if (streamFailed) continue;
                if (typeof data.error === "string") {
                  const safeMessage = getErrorMessage(data.error);
                  setMessages(prev => {
                    const newMessages = [...prev];
                    const lastIndex = newMessages.length - 1;
                    newMessages[lastIndex] = {
                      ...newMessages[lastIndex],
                      content: `\n\n[ERROR] ${safeMessage}`,
                    };
                    return newMessages;
                  });
                  setActiveToolCall(null);
                  streamFailed = true;
                  continue;
                }
                if (data.text) {
                  setMessages(prev => {
                    const newMessages = [...prev];
                    const lastIndex = newMessages.length - 1;
                    newMessages[lastIndex] = {
                      ...newMessages[lastIndex],
                      content: newMessages[lastIndex].content + data.text
                    };
                    return newMessages;
                  });
                }
                if (data.tool_calls && data.tool_calls.length > 0) {
                  setActiveToolCall(prev => {
                    const call = data.tool_calls[0].function;
                    if (!prev) {
                      return { name: call.name, args: call.arguments || "" };
                    }
                    return {
                      name: prev.name || call.name,
                      args: (typeof prev.args === 'string' ? prev.args : "") + (call.arguments || "")
                    };
                  });
                }
              } catch {
                // Ignore incomplete
              }
            }
          }
        }
      }
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: "\n\n[ERROR] The AI chat request could not be completed.",
        },
      ]);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="h-full flex flex-col md:flex-row bg-white border-b-4 border-black text-black">
      
      {/* CỘT TRÁI: KNOWLEDGE BASE */}
      <div className="w-full md:w-1/3 flex flex-col border-r-4 border-black border-b-4 md:border-b-0 min-h-[500px]">
        <div className="p-4 border-b-4 border-black bg-black text-white flex justify-between items-center">
          <h2 className="text-xl font-bold font-mono uppercase">Knowledge Base</h2>
          <span className="material-symbols-outlined font-bold">folder</span>
        </div>
        
        {/* Upload Area */}
        <div className="p-4 border-b-4 border-black bg-white relative space-y-4">
          <div className="flex flex-col gap-2">
            <label className="font-mono text-sm font-bold uppercase text-black">Chủ đề <span className="text-red-500">*</span></label>
            <select
              value={selectedTopicId}
              onChange={(e) => setSelectedTopicId(e.target.value)}
              className="w-full border-4 border-black p-2 font-mono uppercase text-sm font-bold bg-white focus:outline-none"
            >
              <option value="">-- CHỌN CHỦ ĐỀ --</option>
              {topics?.map((topic: Topic) => (
                <option key={topic.id} value={topic.id}>{topic.name}</option>
              ))}
            </select>
          </div>
          
          <div className="border-4 border-dashed border-black p-6 flex flex-col items-center justify-center bg-white hover:bg-gray-100 transition-none group text-center shadow-[4px_4px_0_0_rgba(0,0,0,1)] relative">
            <span className="material-symbols-outlined text-3xl font-bold mb-2">
              {isUploading ? 'sync' : 'cloud_upload'}
            </span>
            <h3 className="text-base font-bold text-black uppercase font-mono">Tải tài liệu lên</h3>
            <p className="text-black font-mono text-xs mt-1">PDF, DOCX, TXT. Max 50MB.</p>
            <input 
              type="file" 
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full disabled:cursor-not-allowed"
              accept=".pdf,.docx,.txt"
              onChange={handleFileUpload}
              disabled={isUploading}
            />
          </div>
        </div>

        {/* List of Materials */}
        <div className="flex-1 p-4 overflow-y-auto bg-gray-50 flex flex-col space-y-4">
          {isLoading && materials.length === 0 ? (
            <div className="text-center p-4"><span className="material-symbols-outlined animate-spin font-bold text-2xl">sync</span></div>
          ) : materials.length === 0 ? (
            <div className="text-center font-bold font-mono text-sm border-4 border-black p-4 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">Chưa có tài liệu nào.</div>
          ) : (
            materials.map((mat) => (
              <div 
                key={mat.id} 
                className={`border-4 border-black p-3 flex flex-col gap-2 transition-none cursor-pointer shadow-[4px_4px_0_0_rgba(0,0,0,1)] ${activeMaterial === mat.id ? 'bg-black text-white' : 'bg-white text-black hover:translate-x-[2px] hover:translate-y-[2px]'}`}
                onClick={() => setActiveMaterial(mat.id)}
              >
                <div className="flex items-center gap-2">
                  <span className={`material-symbols-outlined font-bold ${activeMaterial === mat.id ? 'text-white' : 'text-black'}`}>
                    {activeMaterial === mat.id ? 'radio_button_checked' : 'radio_button_unchecked'}
                  </span>
                  <span className="font-bold font-mono text-sm line-clamp-1 flex-1 uppercase" title={mat.title}>{mat.title}</span>
                </div>
                <div className="flex justify-between items-center pl-8 text-xs font-mono font-bold mt-2">
                  <span className="uppercase">{mat.file_type}</span>
                  <div className="flex items-center gap-2">
                    <span>{mat.ai_status === 'completed' ? '[OK] HOÀN THÀNH' : (mat.ai_status === 'processing' ? '[...] ĐANG XỬ LÝ' : '[WAIT] CHỜ XỬ LÝ')}</span>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        setMaterialToDelete(mat.id);
                      }}
                      className="bg-white text-black border-2 border-black hover:bg-black hover:text-white flex items-center justify-center p-1 transition-none"
                      title="Xóa tài liệu"
                    >
                      <span className="material-symbols-outlined text-sm font-bold">delete</span>
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* CỘT GIỮA: AI CHAT (RIGHT PANE Part 1) */}
      <div className="w-full md:w-1/3 flex flex-col border-r-4 border-black border-b-4 md:border-b-0 min-h-[500px]">
        <div className="p-4 border-b-4 border-black bg-black text-white flex justify-between items-center">
          <h2 className="text-xl font-bold font-mono uppercase">AI Studio</h2>
          <span className="material-symbols-outlined font-bold">smart_toy</span>
        </div>

        {/* Thao tác nhanh (Only active if material selected) */}
        <div className="p-4 border-b-4 border-black bg-white">
          <h3 className="font-bold font-mono uppercase mb-2">Thao tác nhanh</h3>
          {!activeMaterial ? (
            <div className="text-sm font-mono opacity-50 font-bold border-2 border-black border-dashed p-2">Vui lòng chọn 1 tài liệu ở cột trái.</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <label className="font-mono text-sm font-bold uppercase">Số lượng:</label>
                <input 
                  type="number" 
                  min={1} 
                  max={50} 
                  value={questionCount} 
                  onChange={(e) => setQuestionCount(Number(e.target.value))}
                  className="w-20 border-4 border-black p-1 font-mono focus:outline-none"
                />
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={generateQuestions}
                  disabled={isStreaming}
                  className="flex-1 bg-white text-black border-4 border-black font-bold font-mono text-xs p-2 uppercase hover:bg-black hover:text-white transition-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] disabled:opacity-50"
                >
                  Sinh Câu Hỏi
                </button>
                <button 
                  onClick={generateFlashcards}
                  disabled={isStreaming}
                  className="flex-1 bg-white text-black border-4 border-black font-bold font-mono text-xs p-2 uppercase hover:bg-black hover:text-white transition-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] disabled:opacity-50"
                >
                  Tạo Flashcards
                </button>
                <button 
                  onClick={generateTopicBrief}
                  disabled={isStreaming}
                  className="flex-1 bg-white text-black border-4 border-black font-bold font-mono text-xs p-2 uppercase hover:bg-black hover:text-white transition-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] disabled:opacity-50"
                >
                  Tạo Dàn Ý
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Khung chat */}
        <div className="flex-1 p-4 overflow-y-auto bg-gray-50 flex flex-col space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[90%] p-3 border-4 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] ${msg.role === "user" ? "bg-white text-black" : "bg-black text-white"}`}>
                <div className="font-bold font-mono mb-1 uppercase text-xs border-b-2 border-current pb-1">
                  {msg.role === "user" ? user?.full_name || "You" : "AI Assistant"}
                </div>
                <div className="font-mono text-sm whitespace-pre-wrap">
                  {msg.content}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Cảnh báo Guardrails */}
        <div className="px-4 py-2 bg-white border-t-4 border-black text-xs font-mono font-bold text-center">
          [WARNING] AI có thể sinh kết quả sai.
        </div>

        {/* Khung nhập chat */}
        {!activeMaterial && (
          <div className="border-t-4 border-black px-4 py-2 font-mono text-xs font-bold uppercase">
            [REQUIRED] Select a material before starting AI chat.
          </div>
        )}
        <form onSubmit={handleSubmit} className="p-3 bg-white border-t-4 border-black flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming || !activeMaterial}
            placeholder={
              activeMaterial
                ? "Nhập yêu cầu chat..."
                : "Select a material to enable chat"
            }
            className="flex-1 p-2 border-4 border-black font-mono focus:outline-none disabled:bg-gray-200"
          />
          <button 
            type="submit" 
            disabled={isStreaming || !activeMaterial || !input.trim()}
            className="px-4 border-4 border-black bg-black text-white font-bold font-mono hover:bg-white hover:text-black transition-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:opacity-50 flex items-center justify-center"
          >
            {isStreaming ? <Loader2 className="animate-spin w-5 h-5" /> : <Send className="w-5 h-5" />}
          </button>
        </form>
      </div>

      {/* CỘT PHẢI: GENERATIVE UI (RIGHT PANE Part 2) */}
      <div className="w-full md:w-1/3 flex flex-col bg-white border-l-0 md:border-l-4 border-black">
        <GenerativePreview
          toolName={activeToolCall?.name || null}
          toolArgs={activeToolCall?.args || null}
          isStreaming={isStreaming}
        />
      </div>

      <Dialog open={!!materialToDelete} onOpenChange={(open) => !open && setMaterialToDelete(null)}>
        <DialogContent className="border-4 border-black rounded-none shadow-[8px_8px_0_0_rgba(0,0,0,1)] bg-white text-black max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="font-mono font-bold uppercase text-lg border-b-4 border-black pb-2">Xác nhận xóa</DialogTitle>
            <DialogDescription className="font-mono text-black pt-4">
              Bạn có chắc chắn muốn xóa tài liệu này?
              <br/><br/>
              <strong>Lưu ý:</strong> File vật lý sẽ bị xóa để giải phóng dung lượng. Các câu hỏi và flashcard đã được AI sinh ra từ tài liệu này vẫn sẽ được giữ lại trong hệ thống.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-6 flex gap-4 bg-transparent p-0 border-0">
            <button
              onClick={() => setMaterialToDelete(null)}
              className="flex-1 border-4 border-black bg-white text-black font-mono font-bold uppercase p-2 hover:bg-gray-100 transition-none shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
            >
              Hủy
            </button>
            <button
              onClick={handleDeleteMaterial}
              disabled={isDeleting}
              className="flex-1 border-4 border-black bg-black text-white font-mono font-bold uppercase p-2 hover:bg-white hover:text-black transition-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isDeleting ? <Loader2 className="animate-spin w-4 h-4" /> : "Xóa"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
