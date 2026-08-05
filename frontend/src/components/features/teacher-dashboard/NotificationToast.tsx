import React from 'react';

export default function NotificationToast() {
  return (
    <div className="fixed top-6 right-6 md:top-8 md:right-8 bg-white border border-black shadow-[0px_4px_12px_rgba(0,0,0,0.1)] rounded-lg p-4 max-w-sm flex items-start gap-3 z-50">
      <div className="text-black mt-0.5">
        <span className="material-symbols-outlined">auto_awesome</span>
      </div>
      <div>
        <h4 className="text-sm font-bold text-black">AI đã hoàn thành phân tích</h4>
        <p className="text-xs text-gray-500 mt-1">Đề cương Sinh Học Lớp 11 đã sẵn sàng để tạo câu hỏi.</p>
      </div>
      <button className="text-gray-500 hover:text-black ml-auto border border-transparent hover:border-black rounded">
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  );
}
