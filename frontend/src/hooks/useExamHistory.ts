import { useCallback, useState } from "react";
import useSWR from "swr";
import { fetcher } from "./useFetch";
import { updateSubmissionGrade } from "@/services/apiService";
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

export interface SubmissionGradeOverride {
  submission: SubmissionDetail | undefined;
  isLoading: boolean;
  isError: unknown;
  /** The answer whose correction is in flight, or null. Drives disabled states. */
  pendingQuestionId: string | null;
  /** Resolves to whether the server accepted the correction. */
  saveGrade: (
    questionId: string,
    pointsAwarded: number,
    reason: string,
  ) => Promise<boolean>;
  reload: () => Promise<unknown>;
}

/**
 * Owns SWR cache coordination for correcting one submission's answer scores.
 *
 * It reads through `useSubmissionDetail`, so the correction and the rendered
 * submission share a single cache entry and a stored correction is visible
 * everywhere at once. The endpoint returns the whole updated submission --
 * including the recomputed `total_score` and the correction trail -- so an
 * accepted write is placed into the cache directly rather than re-fetched.
 * A refused write revalidates instead, because the server is the only
 * authority on what a refusal left behind and the screen must never keep an
 * optimistic guess.
 *
 * Only one correction is allowed in flight at a time: `total_score` is
 * recomputed server-side from all answers, so two overlapping writes would
 * each return a total computed without the other.
 */
export function useSubmissionGradeOverride(
  submissionId: string | null,
  // `error` comes first so a caller that only reports the failure can take a
  // single parameter; `questionId` is there for one that reports per row.
  onError?: (error: unknown, questionId: string) => void,
): SubmissionGradeOverride {
  const { submission, isLoading, isError, mutate } =
    useSubmissionDetail(submissionId);
  const [pendingQuestionId, setPendingQuestionId] = useState<string | null>(
    null,
  );

  const saveGrade = useCallback(
    async (
      questionId: string,
      pointsAwarded: number,
      reason: string,
    ): Promise<boolean> => {
      if (!submissionId || pendingQuestionId) return false;
      setPendingQuestionId(questionId);
      try {
        const updated = await updateSubmissionGrade(submissionId, questionId, {
          points_awarded: pointsAwarded,
          reason,
        });
        await mutate(updated, { revalidate: false });
        return true;
      } catch (caught) {
        await mutate();
        onError?.(caught, questionId);
        return false;
      } finally {
        setPendingQuestionId(null);
      }
    },
    [mutate, onError, pendingQuestionId, submissionId],
  );

  return {
    submission,
    isLoading,
    isError,
    pendingQuestionId,
    saveGrade,
    reload: mutate,
  };
}
