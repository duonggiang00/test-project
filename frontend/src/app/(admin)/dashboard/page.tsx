"use client";

import { useAnalyticsOverview, useTopicPerformance } from "@/hooks/useAnalytics";
import { StatCard } from "@/components/features/admin/StatCard";
import { TopicPerformanceChart } from "@/components/features/admin/TopicPerformanceChart";
import { Loader2, Users, FileText, HelpCircle, CheckSquare } from "lucide-react";

export default function AdminDashboard() {
  const { overview, isLoading: isOverviewLoading } = useAnalyticsOverview();
  const { topicPerformance, isLoading: isTopicsLoading } = useTopicPerformance();

  const isLoading = isOverviewLoading || isTopicsLoading;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <Loader2 className="h-8 w-8 animate-spin text-black" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8 bg-white min-h-screen text-black">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b-4 border-black pb-4">
        <div>
          <h1 className="text-3xl font-bold text-black uppercase tracking-tight">Tổng quan Dashboard</h1>
          <p className="text-base font-mono text-black mt-1">Theo dõi hoạt động và tiến độ hệ thống AI.</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <StatCard 
          title="Tổng Học Sinh" 
          value={overview?.total_students || 0} 
          icon={Users} 
        />
        <StatCard 
          title="Tổng Số Đề Thi" 
          value={overview?.total_exams || 0} 
          icon={FileText} 
        />
        <StatCard 
          title="Tổng Câu Hỏi" 
          value={overview?.total_questions || 0} 
          icon={HelpCircle} 
        />
        <StatCard 
          title="Lượt Nộp Bài" 
          value={overview?.total_submissions || 0} 
          icon={CheckSquare} 
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 gap-6">
        <div className="border-4 border-black p-4 bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <TopicPerformanceChart data={topicPerformance} />
        </div>
      </div>
    </div>
  );
}
