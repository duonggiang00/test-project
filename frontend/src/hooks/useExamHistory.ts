import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { SubmissionHistoryItem, SubmissionDetail, PaginatedResponse } from "@/types";

export interface UseSubmissionsParams {
  page?: number;
  size?: number;
  student_id?: string;
  exam_id?: string;
  status?: string;
  search?: string;
}

export function useSubmissions(params?: UseSubmissionsParams) {
  const page = params?.page ?? 1;
  const size = params?.size ?? 20;

  const query = new URLSearchParams();
  query.append("page", page.toString());
  query.append("size", size.toString());

  if (params?.student_id) query.append("student_id", params.student_id);
  if (params?.exam_id) query.append("exam_id", params.exam_id);
  if (params?.status) query.append("status", params.status);
  if (params?.search) query.append("search", params.search);

  const key = `/history/submissions?${query.toString()}`;

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<SubmissionHistoryItem>>(
    key,
    fetcher
  );

  return {
    submissions: data?.items || [],
    pagination: {
      items: data?.items || [],
      total: data?.total || 0,
      page: data?.page || 1,
      size: data?.size || 20,
      pages: data?.pages || 1,
    },
    data,
    isLoading,
    isError: error,
    mutate,
  };
}

// Export as useExamHistory for backward compatibility if needed, though useSubmissions is preferred.
export const useExamHistory = useSubmissions;

export function useSubmissionDetail(submissionId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<SubmissionDetail>(
    submissionId ? `/history/submissions/${submissionId}` : null,
    fetcher
  );

  return {
    submission: data,
    isLoading,
    isError: error,
    mutate,
  };
}
