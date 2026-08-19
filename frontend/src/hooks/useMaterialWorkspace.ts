import { useCallback, useState } from "react";
import useSWR from "swr";
import { fetcher } from "./useFetch";
import api from "@/lib/api";
import {
  approveGenerationJob,
  getGenerationJob,
  publishGenerationJob,
  rejectGenerationJob,
  type AIGenerationJob,
  type PublishGenerationJobPayload,
} from "@/services/apiService";
import {
  availableReviewActions,
  type AIGenerationReviewAction,
} from "@/lib/ai-generation-review";

export function useMaterialDetail(materialId: string) {
  const { data, isLoading, mutate } = useSWR(
    materialId ? `/materials/${materialId}` : null,
    fetcher
  );
  return { material: data, isLoading, mutate };
}

export function useMaterialQuestions(materialId: string) {
  const { data, isLoading, mutate } = useSWR(
    materialId ? `/materials/${materialId}/questions` : null,
    fetcher
  );
  return { questions: (data ?? []) as QuestionPreview[], isLoading, mutate };
}

export interface OptionPreview {
  content: string;
  is_correct: boolean;
}

export interface QuestionPreview {
  type: string;
  content: string;
  points: number;
  source_reference?: string;
  options: OptionPreview[];
  metadata_json?: Record<string, unknown>;
}

export interface FlashcardPreview {
  term: string;
  definition: string;
}

/**
 * Generation responses are additive: they keep their original payload key and
 * now also identify the review job the draft was parked in. Nothing is written
 * to the live tables until that job is approved and then published.
 */
export interface GeneratedDraftEnvelope {
  job_id: string;
  status: string;
}

export async function generateQuestions(
  materialId: string,
  payload: { question_types: string[]; count: number; difficulty: string }
): Promise<GeneratedDraftEnvelope & { questions: QuestionPreview[] }> {
  const res = await api.post(`/materials/${materialId}/generate-questions`, payload);
  return res.data;
}

export async function generateFlashcards(
  materialId: string,
  count: number
): Promise<GeneratedDraftEnvelope & { flashcards: FlashcardPreview[] }> {
  const res = await api.post(`/materials/${materialId}/generate-flashcards`, { count });
  return res.data;
}

export interface GenerationJobReview {
  job: AIGenerationJob | undefined;
  isLoading: boolean;
  isError: unknown;
  /** Reviewer actions the backend allowlist accepts for the current status. */
  actions: AIGenerationReviewAction[];
  /** The action currently in flight, or null. Drives disabled/loading states. */
  pendingAction: AIGenerationReviewAction | null;
  /** Each decision resolves to whether the server accepted it. */
  approve: () => Promise<boolean>;
  reject: () => Promise<boolean>;
  publish: (payload?: PublishGenerationJobPayload) => Promise<boolean>;
  reload: () => Promise<unknown>;
}

/**
 * Owns SWR cache coordination for one AI generation job.
 *
 * The server is the only authority on the job's status, so the panel reads it
 * from `GET /ai/generation-jobs/{id}` rather than trusting the status echoed
 * by the generate call. Every decision sends the version it observed, so a
 * reviewer acting on a stale panel gets `AI_JOB_VERSION_CONFLICT` instead of
 * silently overwriting another reviewer's decision.
 */
export function useGenerationJobReview(
  jobId: string | null | undefined,
  onError?: (action: AIGenerationReviewAction, error: unknown) => void,
): GenerationJobReview {
  const key = jobId ? `/ai/generation-jobs/${jobId}` : null;
  const { data, error, isLoading, mutate } = useSWR<AIGenerationJob>(
    key,
    () => getGenerationJob(jobId as string),
  );
  const [pendingAction, setPendingAction] =
    useState<AIGenerationReviewAction | null>(null);

  const run = useCallback(
    async (
      action: AIGenerationReviewAction,
      decide: (job: AIGenerationJob) => Promise<AIGenerationJob | null>,
    ): Promise<boolean> => {
      if (!jobId || !data || pendingAction) return false;
      setPendingAction(action);
      try {
        const updated = await decide(data);
        if (updated) {
          // Approve/reject return the full updated job, so the cache can be
          // written directly. Publish returns a placement result instead, so
          // its caller revalidates rather than inventing a job shape.
          await mutate(updated, { revalidate: false });
        } else {
          await mutate();
        }
        return true;
      } catch (caught) {
        // Refresh from the server so a refused decision leaves the panel
        // showing the real status rather than an optimistic guess.
        await mutate();
        onError?.(action, caught);
        return false;
      } finally {
        setPendingAction(null);
      }
    },
    [data, jobId, mutate, onError, pendingAction],
  );

  const approve = useCallback(
    () =>
      run("approve", (job) => approveGenerationJob(job.id, job.version)),
    [run],
  );

  const reject = useCallback(
    () => run("reject", (job) => rejectGenerationJob(job.id, job.version)),
    [run],
  );

  const publish = useCallback(
    (payload: PublishGenerationJobPayload = {}) =>
      run("publish", async (job) => {
        await publishGenerationJob(job.id, payload, job.version);
        return null;
      }),
    [run],
  );

  return {
    job: data,
    isLoading,
    isError: error,
    actions: availableReviewActions(data?.status),
    pendingAction,
    approve,
    reject,
    publish,
    reload: mutate,
  };
}
