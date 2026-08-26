import { AppIcon } from "@/components/ui/app-icon";
import React from 'react';

export default function RecentExamsList() {
  return (
    <div className="lg:col-span-2 bg-white border-4 border-black flex flex-col shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
      <div className="p-5 border-b-4 border-black flex justify-between items-center bg-white">
        <h3 className="text-xl font-bold text-black uppercase tracking-tight">Recent Exams</h3>
        <button className="text-black font-bold hover:bg-black hover:text-white px-2 py-1 border-2 border-black transition-colors uppercase text-sm">View All</button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-white text-black font-bold border-b-4 border-black uppercase text-sm font-mono">
              <th className="py-3 px-5 border-r-2 border-black">Exam</th>
              <th className="py-3 px-5 border-r-2 border-black">Subject</th>
              <th className="py-3 px-5 border-r-2 border-black">Created</th>
              <th className="py-3 px-5 border-r-2 border-black">Status</th>
              <th className="py-3 px-5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="text-sm font-mono text-black bg-white">
            <tr className="border-b-2 border-black hover:bg-black hover:text-white transition-colors group">
              <td className="py-4 px-5 font-bold border-r-2 border-black group-hover:border-white">Grade 10 Math Midterm</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">Mathematics</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">12/10/2023</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">
                <span className="inline-flex items-center px-2 py-1 border-2 border-black text-xs font-bold bg-white text-black uppercase">
                  Complete
                </span>
              </td>
              <td className="py-4 px-5 text-right">
                <button className="text-black group-hover:text-white hover:scale-110 transition-transform"><AppIcon name="more_vert" className="size-5" /></button>
              </td>
            </tr>
            <tr className="border-b-2 border-black hover:bg-black hover:text-white transition-colors group">
              <td className="py-4 px-5 font-bold border-r-2 border-black group-hover:border-white">Physics Chapter 2 Review</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">Physics</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">10/10/2023</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">
                <span className="inline-flex items-center px-2 py-1 border-2 border-black text-xs font-bold bg-white text-black uppercase">
                  Processing
                </span>
              </td>
              <td className="py-4 px-5 text-right">
                <button className="text-black group-hover:text-white hover:scale-110 transition-transform"><AppIcon name="more_vert" className="size-5" /></button>
              </td>
            </tr>
            <tr className="hover:bg-black hover:text-white transition-colors group">
              <td className="py-4 px-5 font-bold border-r-2 border-black group-hover:border-white">English Graduation Practice Exam</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">English</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">08/10/2023</td>
              <td className="py-4 px-5 border-r-2 border-black group-hover:border-white">
                <span className="inline-flex items-center px-2 py-1 border-2 border-black text-xs font-bold bg-white text-black uppercase">
                  Draft
                </span>
              </td>
              <td className="py-4 px-5 text-right">
                <button className="text-black group-hover:text-white hover:scale-110 transition-transform"><AppIcon name="more_vert" className="size-5" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
