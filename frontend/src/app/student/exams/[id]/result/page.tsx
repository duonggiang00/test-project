"use client";

import React, { use } from "react";
import { ExamResultView } from "@/components/features/student/ExamResultView";

export default function ExamResultPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);

  return <ExamResultView examId={resolvedParams.id} />;
}
