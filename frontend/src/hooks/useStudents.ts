import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { StudentUser, StudentDetail, PaginatedResponse } from "@/types";

export interface UseStudentsParams {
  page?: number;
  size?: number;
  search?: string;
}

export function useStudents(params?: UseStudentsParams) {
  const page = params?.page ?? 1;
  const size = params?.size ?? 50;
  const searchParam = params?.search ? `&search=${encodeURIComponent(params.search)}` : "";
  const key = `/admin/users?role=student&page=${page}&size=${size}${searchParam}`;

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<StudentUser> | StudentUser[]>(key, fetcher);

  const students: StudentUser[] = Array.isArray(data) ? data : data?.items || [];
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
    students,
    pagination,
    data,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useStudentDetail(studentId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<StudentDetail>(
    studentId ? `/admin/users/${studentId}` : null,
    fetcher
  );

  return {
    student: data,
    isLoading,
    isError: error,
    mutate,
  };
}
