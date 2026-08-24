"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTopics } from "@/hooks/useTopics";
import { Topic } from "@/types";
import { Loader2, Folder, FolderOpen, FileText } from "lucide-react";

export default function TopicDetailLayout({ children }: { children: React.ReactNode }) {
  const { id: currentTopicId } = useParams() as { id: string };
  const { topics, isLoading } = useTopics({ page: 1, size: 1000 });

  // Build tree
  const rootTopics = topics.filter(t => !t.parent_id);
  const getChildren = (parentId: string) => topics.filter(t => t.parent_id === parentId);

  const TopicTreeItem = ({ topic, level }: { topic: Topic, level: number }) => {
    const children = getChildren(topic.id);
    const hasChildren = children.length > 0;
    const isCurrent = topic.id === currentTopicId;
    const [isOpen, setIsOpen] = useState(true);

    return (
      <div className="flex flex-col">
        <div 
          className={`flex items-center gap-2 py-2 px-2 cursor-pointer border-l-4 transition-colors ${
            isCurrent ? "border-black bg-black text-white font-bold" : "border-transparent hover:bg-white text-black"
          }`}
          style={{ paddingLeft: `${level * 1.5 + 0.5}rem` }}
        >
          {hasChildren ? (
            <button onClick={() => setIsOpen(!isOpen)} className="focus:outline-none shrink-0">
              {isOpen ? <FolderOpen className="w-4 h-4" /> : <Folder className="w-4 h-4" />}
            </button>
          ) : (
            <FileText className="w-4 h-4 shrink-0 opacity-50" />
          )}
          <Link href={`/topics/${topic.id}`} className="flex-1 truncate uppercase">
            {topic.name}
          </Link>
        </div>
        {hasChildren && isOpen && (
          <div className="flex flex-col">
            {children.map(child => (
              <TopicTreeItem key={child.id} topic={child} level={level + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col md:flex-row min-h-screen bg-white">
      {/* Topic Tree Sidebar */}
      <aside className="w-full md:w-64 shrink-0 border-r-4 border-black flex flex-col h-[300px] md:h-auto overflow-y-auto">
        <div className="p-4 border-b-4 border-black bg-white sticky top-0 z-10 shadow-[0_4px_0_0_rgba(0,0,0,1)]">
          <h2 className="font-bold uppercase text-lg text-black">Topic Tree</h2>
        </div>
        <div className="p-2 font-mono text-sm">
          {isLoading ? (
            <div className="flex justify-center p-4">
              <Loader2 className="w-6 h-6 animate-spin text-black" />
            </div>
          ) : (
            rootTopics.map(t => <TopicTreeItem key={t.id} topic={t} level={0} />)
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-x-hidden">
        {children}
      </main>
    </div>
  );
}
