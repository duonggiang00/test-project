"use client";

import React from "react";
import { useScoreStats } from "@/hooks/useAnalytics";

export default function ReportsPage() {
  const { scoreStats, isLoading, isError } = useScoreStats();

  if (isLoading) {
    return (
      <div className="p-8">
        <p className="text-black font-bold font-mono">Loading reports...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8">
        <p className="text-black font-bold border-4 border-black p-4 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono">
          Error loading reports.
        </p>
      </div>
    );
  }

  const highestScore = scoreStats?.highest_score ?? 0;
  const lowestScore = scoreStats?.lowest_score ?? 0;
  const averageScore = scoreStats?.average_score ?? 0;
  const distribution = scoreStats?.distribution ?? [];

  return (
    <div className="p-8 bg-white min-h-screen text-black">
      <h1 className="text-2xl font-bold mb-6 pb-2 border-b-4 border-black font-mono uppercase">
        Reports
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
          <h2 className="text-lg font-bold mb-2 font-mono uppercase">Highest Score</h2>
          <p className="text-4xl font-black font-mono">{highestScore}</p>
        </div>

        <div className="border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
          <h2 className="text-lg font-bold mb-2 font-mono uppercase">Lowest Score</h2>
          <p className="text-4xl font-black font-mono">{lowestScore}</p>
        </div>

        <div className="border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
          <h2 className="text-lg font-bold mb-2 font-mono uppercase">Average Score</h2>
          <p className="text-4xl font-black font-mono">{typeof averageScore === 'number' ? averageScore.toFixed(1) : averageScore}</p>
        </div>
      </div>

      <div className="border-4 border-black bg-white shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
        <div className="p-4 border-b-4 border-black bg-white">
          <h2 className="text-xl font-bold font-mono uppercase">Score Distribution</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white border-b-4 border-black">
                <th className="p-4 font-bold border-r-4 border-black font-mono uppercase">Range</th>
                <th className="p-4 font-bold font-mono uppercase">Count</th>
              </tr>
            </thead>
            <tbody>
              {distribution.length === 0 ? (
                <tr>
                  <td
                    colSpan={2}
                    className="p-4 text-center border-b-4 border-black font-bold font-mono uppercase"
                  >
                    No data available
                  </td>
                </tr>
              ) : (
                distribution.map((bucket, index) => (
                  <tr
                    key={index}
                    className="border-b-4 border-black last:border-b-0"
                  >
                    <td className="p-4 border-r-4 border-black font-mono font-bold">
                      {bucket.range_label}
                    </td>
                    <td className="p-4 font-bold font-mono">{bucket.count}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
