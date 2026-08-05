import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { Exam, ExamDetail, PaginatedResponse, Question } from "@/types";
import type { QuestionCreate } from "./useQuestions";
import api from "@/lib/api";

export interface UseExamsParams {
  page?: number;
  size?: number;
  search?: string;
  topic_id?: string;
}

export function useExams(params?: UseExamsParams) {
  const page = params?.page ?? 1;
  const size = params?.size ?? 50;

  const searchParams = new URLSearchParams();
  searchParams.append("page", page.toString());
  searchParams.append("size", size.toString());

  if (params?.search) {
    searchParams.append("search", params.search);
  }
  if (params?.topic_id) {
    searchParams.append("topic_id", params.topic_id);
  }

  const key = `/exams?${searchParams.toString()}`;

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<Exam>>(key, fetcher);

  const exams: Exam[] = data?.items || [];
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
        size: 50,
        pages: 1,
      };

  return {
    exams,
    pagination,
    data,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useExamDetail(examId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ExamDetail>(
    examId ? `/exams/${examId}` : null,
    fetcher
  );

  return {
    exam: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export interface ExamCreate {
  title: string;
  description?: string | null;
  duration_minutes: number;
  is_published: boolean;
  topic_id?: string | null;
}

export type ExamUpdate = Partial<ExamCreate>;

export const createExam = async (exam: ExamCreate): Promise<Exam> => {
  const response = await api.post("/exams", exam);
  return response.data;
};

export const updateExam = async (examId: string, exam: ExamUpdate): Promise<Exam> => {
  const response = await api.put(`/exams/${examId}`, exam);
  return response.data;
};

export const deleteExam = async (examId: string): Promise<void> => {
  await api.delete(`/exams/${examId}`);
};

export const createExamQuestion = async (examId: string, data: QuestionCreate): Promise<Question> => {
  const response = await api.post(`/exams/${examId}/questions`, data);
  return response.data;
};
