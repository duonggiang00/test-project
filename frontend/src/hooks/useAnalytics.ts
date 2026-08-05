import useSWR from "swr";
import { fetcher } from "./useFetch";
import type {
  AnalyticsOverview,
  ScoreStats,
  CompletionStatus,
  TopicPerformance,
} from "@/types";

export function useAnalyticsOverview(student_id_or_all?: string) {
  const query = student_id_or_all && student_id_or_all !== "all" 
    ? `?student_id=${encodeURIComponent(student_id_or_all)}` 
    : "";
  const { data, error, isLoading, mutate } = useSWR<AnalyticsOverview>(
    `/analytics/overview${query}`,
    fetcher
  );

  return {
    overview: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export interface UseScoreStatsParams {
  exam_id?: string;
  topic_id?: string;
}

export function useScoreStats(params?: UseScoreStatsParams) {
  const examParam = params?.exam_id ? `exam_id=${encodeURIComponent(params.exam_id)}` : "";
  const topicParam = params?.topic_id ? `topic_id=${encodeURIComponent(params.topic_id)}` : "";
  const query = [examParam, topicParam].filter(Boolean).join("&");
  const key = `/analytics/score-stats${query ? `?${query}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR<ScoreStats>(key, fetcher);

  return {
    scoreStats: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useCompletionStatus(examId?: string) {
  const key = examId
    ? `/analytics/completion-status?exam_id=${encodeURIComponent(examId)}`
    : "/analytics/completion-status";

  const { data, error, isLoading, mutate } = useSWR<CompletionStatus>(key, fetcher);

  return {
    completionStatus: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useTopicPerformance() {
  const { data, error, isLoading, mutate } = useSWR<TopicPerformance[]>(
    "/analytics/topic-performance",
    fetcher
  );

  return {
    topicPerformance: data || [],
    isLoading,
    isError: error,
    mutate,
  };
}

export function useAnalytics(student_id_or_all?: string) {
  const { overview, isLoading: overviewLoading, isError: overviewError, mutate: mutateOverview } = useAnalyticsOverview(student_id_or_all);
  const { scoreStats, isLoading: statsLoading, isError: statsError, mutate: mutateStats } = useScoreStats();
  const { completionStatus, isLoading: completionLoading, isError: completionError, mutate: mutateCompletion } = useCompletionStatus();
  const { topicPerformance, isLoading: topicLoading, isError: topicError, mutate: mutateTopic } = useTopicPerformance();

  const isLoading = overviewLoading || statsLoading || completionLoading || topicLoading;
  const error = overviewError || statsError || completionError || topicError;

  const mutate = () => {
    mutateOverview();
    mutateStats();
    mutateCompletion();
    mutateTopic();
  };

  return {
    overview,
    scoreStats,
    completionStatus,
    topicPerformance,
    isLoading,
    error,
    isError: error,
    mutate,
  };
}
