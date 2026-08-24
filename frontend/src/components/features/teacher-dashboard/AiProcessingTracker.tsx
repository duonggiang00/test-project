import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

export default function AiProcessingTracker() {
  return (
    <div className="bg-white border border-black rounded-xl flex flex-col">
      <div className="p-5 border-b border-black">
        <h3 className="text-xl font-bold text-black flex items-center gap-2">
          <AppIcon name="smart_toy" className="text-black" />
          Tiến Độ AI Xử Lý
        </h3>
      </div>
      <div className="p-5 space-y-5">
        {/* Task 1 */}
        <div className="flex items-start gap-4">
          <div className="mt-1 w-8 h-8 rounded bg-white flex items-center justify-center text-black border border-black flex-shrink-0">
            <AppIcon name="sync" className="size-[18px] animate-spin" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold text-black">Trích xuất câu hỏi từ PDF</p>
            <p className="text-xs text-black mb-2">Đề cương Sinh Học Lớp 11</p>
            <div className="w-full bg-white rounded-full h-1.5 border border-black">
              <div className="bg-white h-1.5 rounded-full" style={{ width: '65%' }}></div>
            </div>
            <div className="flex justify-between text-[10px] text-black mt-1">
              <span>65%</span>
              <span>Còn ~2 phút</span>
            </div>
          </div>
        </div>
        {/* Task 2 */}
        <div className="flex items-start gap-4">
          <div className="mt-1 w-8 h-8 rounded bg-white flex items-center justify-center text-black border border-black flex-shrink-0">
            <AppIcon name="check" className="size-[18px]" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold text-black">Tạo ma trận đề thi</p>
            <p className="text-xs text-black mb-2">Kiểm tra Hóa Học 15p</p>
            <div className="w-full bg-white rounded-full h-1.5 border border-black">
              <div className="bg-white h-1.5 rounded-full" style={{ width: '100%' }}></div>
            </div>
            <div className="flex justify-between text-[10px] text-black mt-1">
              <span>Hoàn tất</span>
            </div>
          </div>
        </div>
        {/* Task 3 */}
        <div className="flex items-start gap-4">
          <div className="mt-1 w-8 h-8 rounded bg-white flex items-center justify-center text-black border border-black flex-shrink-0">
            <AppIcon name="schedule" className="size-[18px]" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold text-black">Dịch câu hỏi sang Tiếng Anh</p>
            <p className="text-xs text-black mb-2">Bộ 50 câu Toán Logic</p>
            <div className="w-full bg-white rounded-full h-1.5 border border-black">
              <div className="bg-white h-1.5 rounded-full" style={{ width: '0%' }}></div>
            </div>
            <div className="flex justify-between text-[10px] text-black mt-1">
              <span>Đang chờ...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
