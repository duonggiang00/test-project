"use client";

import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { StudentExamList, StudentExamDetail, PaginatedResponse } from "@/types";

export interface UseStudentExamsParams {
  page?: number;
  size?: number;
  search?: string;
  topic_id?: string;
}

export function useStudentExams(params?: UseStudentExamsParams) {
  const page = params?.page ?? 1;
  const size = params?.size ?? 4;

  const searchParams = new URLSearchParams();
  searchParams.append("page", page.toString());
  searchParams.append("size", size.toString());

  if (params?.search) {
    searchParams.append("search", params.search);
  }
  if (params?.topic_id) {
    searchParams.append("topic_id", params.topic_id);
  }

  const key = `/student/exams?${searchParams.toString()}`;

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<StudentExamList>>(key, fetcher);

  const exams: StudentExamList[] = data?.items || [];
  const pagination = data
    ? {
        items: data.items,
        total: data.total,
        page: data.page,
        size: data.size,
        pages: data.pages,
      }
    : {
        items: [],
        total: 0,
        page: 1,
        size: 4,
        pages: 1,
      };

  return {
    exams,
    pagination,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useTakeExam(examId: string) {
  const { data, error, isLoading } = useSWR<StudentExamDetail>(
    examId ? `/student/exams/${examId}/start` : null,
    fetcher
  );

  return {
    exam: data,
    isLoading,
    isError: error,
  };
}

export function useStudentExamResult(examId: string) {
  const { data, error, isLoading } = useSWR<import("@/types").StudentExamResultResponse>(
    examId ? `/student/exams/${examId}/result` : null,
    fetcher
  );

  return {
    result: data,
    isLoading,
    isError: error,
  };
}

import api from "@/lib/api";

export async function submitExam(examId: string, payload: Record<string, unknown>) {
  const response = await api.post(`/student/exams/${examId}/submit`, payload);
  return response.data;
}
