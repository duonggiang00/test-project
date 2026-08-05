import React from 'react';

export default function RecentExamsList() {
  return (
    <div className="lg:col-span-2 bg-white border-4 border-black flex flex-col shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
      <div className="p-5 border-b-4 border-black flex justify-between items-center bg-white">
        <h3 className="text-xl font-bold text-black uppercase tracking-tight">Đề Thi Gần Đây</h3>
        <button className="text-black font-bold hover:bg-black hover:text-white px-2 py-1 border-2 border-black transition-colors uppercase text-sm">Xem Tất Cả</button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-white text-black font-bold border-b-4 border-black uppercase text-sm font-mono">
              <th className="py-3 px-5 border-r-2 border-black">Tên Đề Thi</th>
              <th className="py-3 px-5 border-r-2 border-black">Môn Học</th>
              <th className="py-3 px-5 border-r-2 border-black">Ngày Tạo</th>
              <th className="py-3 px-5 border-r-2 border-black">Trạng Thái</th>
              <th className="py-3 px-5 text-right">Thao Tác</th>
            </tr>
          </thead>
          <tbody className="text-sm font-mono text-black bg-white">
            <tr className="border-b-2 border-black hover:bg-black hover:text-white transition-colors group">
              <td className="py-4 px-5 font-bold border-r-2 border-black group-hover:border-white">Kiểm Tra Giữa Kỳ Toán 10</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">Toán Học</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">12/10/2023</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">
                <span className="inline-flex items-center px-2 py-1 border-2 border-black text-xs font-bold bg-white text-black uppercase">
                  Hoàn Thành
                </span>
              </td>
              <td className="py-4 px-5 text-right">
                <button className="text-black group-hover:text-white hover:scale-110 transition-transform"><span className="material-symbols-outlined text-[20px]">more_vert</span></button>
              </td>
            </tr>
            <tr className="border-b-2 border-black hover:bg-black hover:text-white transition-colors group">
              <td className="py-4 px-5 font-bold border-r-2 border-black group-hover:border-white">Ôn Tập Vật Lý Chương 2</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">Vật Lý</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">10/10/2023</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">
                <span className="inline-flex items-center px-2 py-1 border-2 border-black text-xs font-bold bg-white text-black uppercase">
                  Đang Xử Lý
                </span>
              </td>
              <td className="py-4 px-5 text-right">
                <button className="text-black group-hover:text-white hover:scale-110 transition-transform"><span className="material-symbols-outlined text-[20px]">more_vert</span></button>
              </td>
            </tr>
            <tr className="hover:bg-black hover:text-white transition-colors group">
              <td className="py-4 px-5 font-bold border-r-2 border-black group-hover:border-white">Đề Thi Thử Tiếng Anh THPTQG</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">Tiếng Anh</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">08/10/2023</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">
                <span className="inline-flex items-center px-2 py-1 border-2 border-black text-xs font-bold bg-white text-black uppercase">
                  Bản Nháp
                </span>
              </td>
              <td className="py-4 px-5 text-right">
                <button className="text-black group-hover:text-white hover:scale-110 transition-transform"><span className="material-symbols-outlined text-[20px]">more_vert</span></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
