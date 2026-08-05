import React from 'react';
import DashboardStatCard from './DashboardStatCard';
import RecentExamsList from './RecentExamsList';
import AiProcessingTracker from './AiProcessingTracker';
import NotificationToast from './NotificationToast';

export default function TeacherDashboardScreen() {
  return (
    <div className="p-4 md:p-8 max-w-container-max mx-auto space-y-8 bg-white min-h-screen text-black">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b-4 border-black pb-4">
        <div>
          <h1 className="text-3xl font-bold text-black uppercase tracking-tight">Tổng quan Dashboard</h1>
          <p className="text-base font-mono text-black mt-1">Theo dõi hoạt động và tiến độ hệ thống AI.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="p-2 border-4 border-black bg-white text-black hover:bg-black hover:text-white transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
            <span className="material-symbols-outlined">download</span>
          </button>
          <button className="px-4 py-2 bg-black text-white font-bold flex items-center gap-2 border-4 border-black hover:bg-white hover:text-black transition-colors shadow-[4px_4px_0_0_rgba(0,0,0,1)] uppercase tracking-tight">
            <span className="material-symbols-outlined text-[18px]">filter_list</span>
            Lọc Dữ Liệu
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <DashboardStatCard
          icon="description"
          trend={{ type: 'up', value: '+12%', icon: 'trending_up' }}
          title="Tổng Số Đề Thi"
          value="1,248"
        />
        <DashboardStatCard
          icon="smart_toy"
          trend={{ type: 'up', value: '+24%', icon: 'trending_up' }}
          title="Câu Hỏi AI Tạo"
          value="15.4k"
        />
        <DashboardStatCard
          icon="group"
          title="Học Sinh Đăng Ký"
          value="3,892"
        />
        <DashboardStatCard
          icon="check_circle"
          trend={{ type: 'down', value: '-2%', icon: 'trending_down' }}
          title="Lượt Nộp Bài"
          value="42.1k"
        />
      </div>

      {/* Bento Layout Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <RecentExamsList />
        <AiProcessingTracker />
      </div>

      <NotificationToast />
    </div>
  );
}
