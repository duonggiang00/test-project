import { useEffect } from "react";
import useSWR from "swr";

import { useUserStore } from "@/lib/store";

export interface CurrentUser {
  id: string;
  email: string;
  role: "admin" | "teacher" | "student";
  full_name: string | null;
  is_active: boolean;
}

class CurrentUserError extends Error {
  constructor(readonly status: number) {
    super("CURRENT_USER_REQUEST_FAILED");
  }
}

async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await fetch("/api/proxy/auth/me", {
    method: "GET",
    cache: "no-store",
  });
  if (!response.ok) throw new CurrentUserError(response.status);
  return response.json() as Promise<CurrentUser>;
}

export function useCurrentUser() {
  const setUser = useUserStore((state) => state.setUser);
  const clearUser = useUserStore((state) => state.clearUser);
  const result = useSWR<CurrentUser, CurrentUserError>(
    "/auth/me",
    fetchCurrentUser,
    { shouldRetryOnError: false },
  );

  useEffect(() => {
    if (result.data) setUser(result.data);
    else if (result.error) clearUser();
  }, [clearUser, result.data, result.error, setUser]);

  return result;
}
