import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { Question, PaginatedResponse, QuestionType, DifficultyLevel } from "@/types";
import api from "@/lib/api";

export interface UseQuestionsParams {
  page?: number;
  size?: number;
  topic_id?: string;
  difficulty?: string;
  search?: string;
  exam_id?: string;
}

export function useQuestions(params?: UseQuestionsParams) {
  const page = params?.page ?? 1;
  const size = params?.size ?? 50;
  
  const queryParams = new URLSearchParams();
  queryParams.append("page", page.toString());
  queryParams.append("size", size.toString());
  if (params?.topic_id) queryParams.append("topic_id", params.topic_id);
  if (params?.difficulty) queryParams.append("difficulty", params.difficulty);
  if (params?.search) queryParams.append("search", params.search);
  if (params?.exam_id) queryParams.append("exam_id", params.exam_id);

  const key = `/questions?${queryParams.toString()}`;

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<Question> | Question[]>(key, fetcher);

  const questions: Question[] = Array.isArray(data) ? data : data?.items || [];
  const pagination = Array.isArray(data)
    ? { items: data, total: data.length, page: 1, size: data.length, pages: 1 }
    : {
        items: data?.items || [],
        total: data?.total || 0,
        page: data?.page || 1,
        size: data?.size || 50,
        pages: data?.pages || 1,
      };

  return {
    questions,
    pagination,
    data,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useQuestionDetail(questionId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Question>(
    questionId ? `/questions/${questionId}` : null,
    fetcher
  );

  return {
    question: data,
    isLoading,
    isError: error,
    mutate,
  };
}

// Mutate Wrappers
export interface OptionCreate {
  content: string;
  is_correct: boolean;
}

export interface QuestionCreate {
  content: string;
  points: number;
  question_type: QuestionType;
  difficulty: DifficultyLevel;
  topic_id?: string | null;
  metadata_json?: Record<string, unknown> | null;
  options: OptionCreate[];
}

export interface QuestionUpdate {
  content?: string;
  points?: number;
  question_type?: QuestionType;
  difficulty?: DifficultyLevel;
  topic_id?: string | null;
  metadata_json?: Record<string, unknown> | null;
  options?: OptionCreate[];
}

export const createQuestion = async (data: QuestionCreate): Promise<Question> => {
  const response = await api.post("/questions", data);
  return response.data;
};

export const updateQuestion = async (questionId: string, data: QuestionUpdate): Promise<Question> => {
  const response = await api.put(`/questions/${questionId}`, data);
  return response.data;
};

export const deleteQuestion = async (questionId: string): Promise<void> => {
  await api.delete(`/questions/${questionId}`);
};
