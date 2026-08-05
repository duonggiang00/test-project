import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { User, PaginatedResponse } from "@/types";
import api from "@/lib/api";

export function useUsers(page: number = 1, size: number = 50) {
  const key = `/admin/users?page=${page}&size=${size}`;

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<User>>(key, fetcher);

  return {
    users: data?.items || [],
    data,
    isLoading,
    isError: error,
    mutate,
  };
}

export const updateUserRole = async (userId: string, newRole: string): Promise<User> => {
  const response = await api.put<User>(`/admin/users/${userId}/role?new_role=${encodeURIComponent(newRole)}`);
  return response.data;
};

export const deleteUser = async (userId: string): Promise<void> => {
  await api.delete(`/admin/users/${userId}`);
};

export function useUserDetail(userId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<User>(
    userId ? `/admin/users/${userId}` : null,
    fetcher
  );

  return {
    user: data,
    isLoading,
    isError: error,
    mutate,
  };
}
