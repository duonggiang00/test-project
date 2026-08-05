"use client";

import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { User } from "@/types";
import api from "@/lib/api";

export function useProfile() {
  const { data, error, isLoading, mutate } = useSWR<User>("/auth/me", fetcher);

  return {
    profile: data,
    user: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export interface ProfileUpdateData {
  full_name?: string | null;
  phone_number?: string | null;
  date_of_birth?: string | null;
  bio?: string | null;
}

export const updateProfile = async (data: ProfileUpdateData): Promise<User> => {
  const payload = { ...data };
  if (payload.date_of_birth === "") {
    payload.date_of_birth = null;
  }
  const response = await api.put("/auth/me", payload);
  return response.data;
};

export const updatePassword = async (data: Record<string, string>): Promise<{message: string}> => {
  const response = await api.put("/auth/me/password", data);
  return response.data;
};

export const uploadAvatar = async (file: File): Promise<User> => {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await api.post("/auth/me/avatar", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};
