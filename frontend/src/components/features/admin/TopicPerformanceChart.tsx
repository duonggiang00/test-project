"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";
import { TopicPerformance } from "@/types";

interface TopicPerformanceChartProps {
  data: TopicPerformance[];
}

export function TopicPerformanceChart({ data }: TopicPerformanceChartProps) {
  return (
    <div className="border-4 border-black bg-white p-5 shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
      <h3 className="text-lg font-bold text-black mb-4 font-mono uppercase">Topic Performance</h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="0" stroke="#000000" vertical={false} />
            <XAxis 
              dataKey="topic_name" 
              stroke="#000000" 
              tick={{ fill: "#000000", fontSize: 12, fontFamily: "monospace" }} 
              axisLine={{ stroke: "#000000", strokeWidth: 2 }}
              tickLine={{ stroke: "#000000", strokeWidth: 2 }}
            />
            <YAxis 
              stroke="#000000" 
              tick={{ fill: "#000000", fontSize: 12, fontFamily: "monospace" }}
              axisLine={{ stroke: "#000000", strokeWidth: 2 }}
              tickLine={{ stroke: "#000000", strokeWidth: 2 }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: "#ffffff", 
                border: "4px solid #000000",
                borderRadius: 0,
                color: "#000000",
                fontFamily: "monospace",
                boxShadow: "4px 4px 0 0 rgba(0,0,0,1)"
              }}
              itemStyle={{ color: "#000000", fontWeight: "bold" }}
              cursor={{ fill: "#ffffff" }}
            />
            <Bar 
              dataKey="avg_score_percentage" 
              fill="#000000" 
              isAnimationActive={false}
              radius={0}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
