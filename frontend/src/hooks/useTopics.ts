import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { Topic, PaginatedResponse } from "@/types";
import api from "@/lib/api";

export interface UseTopicsParams {
  page?: number;
  size?: number;
  search?: string;
}

export function useTopics(params?: UseTopicsParams) {
  const page = params?.page ?? 1;
  const size = params?.size ?? 50;
  const searchParam = params?.search ? `&search=${encodeURIComponent(params.search)}` : "";
  const key = `/topics?page=${page}&size=${size}${searchParam}`;

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<Topic> | Topic[]>(key, fetcher);

  const topics: Topic[] = Array.isArray(data) ? data : data?.items || [];
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
    topics,
    pagination,
    data,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useTopicDetail(topicId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Topic>(
    topicId ? `/topics/${topicId}` : null,
    fetcher
  );

  return {
    topic: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export interface TopicCreate {
  name: string;
  description?: string | null;
  parent_id?: string | null;
}

export interface TopicUpdate {
  name?: string | null;
  description?: string | null;
  parent_id?: string | null;
}

export const createTopic = async (data: TopicCreate): Promise<Topic> => {
  const response = await api.post<Topic>("/topics", data);
  return response.data;
};

export const updateTopic = async (topicId: string, data: TopicUpdate): Promise<Topic> => {
  const response = await api.put<Topic>(`/topics/${topicId}`, data);
  return response.data;
};

export const deleteTopic = async (topicId: string): Promise<void> => {
  await api.delete(`/topics/${topicId}`);
};

export function useTopicProgress(topicId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<{ progress: number }>(
    topicId ? `/topics/${topicId}/progress` : null,
    fetcher
  );

  return {
    progress: data?.progress || 0,
    isLoading,
    isError: error,
    mutate,
  };
}
