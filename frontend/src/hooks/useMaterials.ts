import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { Material, PaginatedResponse } from "@/types";

export function useMaterials(pollingInterval = 0) {
  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<Material>>("/materials", fetcher, {
    refreshInterval: pollingInterval,
  });

  return {
    materials: data?.items || [],
    isLoading,
    isError: error,
    mutate,
  };
}
