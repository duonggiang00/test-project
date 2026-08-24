import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

export default function NotificationToast() {
  return (
    <div className="fixed top-6 right-6 md:top-8 md:right-8 bg-white border border-black shadow-[0px_4px_12px_rgba(0,0,0,1)] rounded-lg p-4 max-w-sm flex items-start gap-3 z-50">
      <div className="text-black mt-0.5">
        <AppIcon name="auto_awesome" className="" />
      </div>
      <div>
        <h4 className="text-sm font-bold text-black">AI đã hoàn thành phân tích</h4>
        <p className="text-xs text-black mt-1">Đề cương Sinh Học Lớp 11 đã sẵn sàng để tạo câu hỏi.</p>
      </div>
      <button className="text-black hover:text-black ml-auto border border-transparent hover:border-black rounded">
        <AppIcon name="close" className="size-[18px]" />
      </button>
    </div>
  );
}
