"use client";

import { AppIcon } from "@/components/ui/app-icon";

import WelcomeBanner from "@/components/features/student-home/WelcomeBanner";
import FeaturedExamList from "@/components/features/student-home/FeaturedExamList";
import { useProfile } from "@/hooks/useProfile";
import { useUserStore } from "@/lib/store";
import { useTopics } from "@/hooks/useTopics";
import Link from "next/link";
import { Loader2 } from "lucide-react";

export default function StudentHomePage() {
  const { user: storeUser } = useUserStore();
  const { profile } = useProfile();
  const currentUser = profile || storeUser;
  const studentName = currentUser?.full_name?.split(" ")[0] || currentUser?.full_name || "Student";

  const { topics, isLoading, isError } = useTopics();

  return (
    <div className="bg-white min-h-screen text-black p-4 md:p-8 max-w-[1200px] mx-auto flex flex-col gap-8 w-full">
      <WelcomeBanner studentName={studentName} />

      <FeaturedExamList />
      
      <div className="flex justify-between items-end border-b-4 border-black pb-4 mt-8">
        <div>
          <h1 className="font-mono text-3xl md:text-5xl font-black uppercase tracking-tight">Topic Library</h1>
          <p className="font-mono mt-2 font-bold uppercase text-black">
            Explore subjects, review flashcards, and take exams
          </p>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-10 w-10 animate-spin text-black" />
        </div>
      )}

      {isError && (
        <div role="alert" className="p-4 border-4 border-dashed border-black bg-white text-black font-mono font-bold uppercase text-center shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
          Topic data could not be loaded.
        </div>
      )}

      {!isLoading && !isError && topics && topics.length === 0 && (
        <div className="p-10 border-4 border-dashed border-black bg-white text-black font-mono font-bold uppercase text-center shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
          No topics are available yet.
        </div>
      )}

      {!isLoading && !isError && topics && topics.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {topics.map((topic) => (
            <Link 
              key={topic.id} 
              href={`/student/topics/${topic.id}`}
              className="group flex flex-col bg-white border-4 border-black p-6 shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-[8px_8px_0_0_rgba(0,0,0,1)] hover:-translate-y-1 transition-all"
            >
              <div className="w-12 h-12 bg-black text-white flex items-center justify-center mb-4 border-2 border-black group-hover:bg-white group-hover:text-black transition-colors">
                <AppIcon name="auto_stories" className="" />
              </div>
              <h2 className="font-mono text-xl font-black uppercase mb-2 line-clamp-2">
                {topic.name}
              </h2>
              <p className="font-mono text-sm font-medium text-black line-clamp-3 mb-4 flex-1">
                {topic.description || "No description"}
              </p>
              <div className="flex items-center text-sm font-mono font-bold uppercase text-black mt-auto">
                Start learning <AppIcon name="arrow_forward" className="ml-1" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
