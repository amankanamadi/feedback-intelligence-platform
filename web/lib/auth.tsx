"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Me } from "@/types/auth";

type AuthContextValue = {
  user: Me | null;
  isLoading: boolean;
};

const AuthContext = createContext<AuthContextValue>({ user: null, isLoading: true });

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = useQuery<Me>({
    queryKey: ["auth", "me"],
    queryFn: () => apiFetch<Me>("/auth/me"),
    retry: false,
    staleTime: 60_000,
    // A logged-out visitor hitting a public page is the common case, not
    // an error - don't let react-query rethrow this into an error
    // boundary; just surface user=null.
    throwOnError: false,
  });

  return <AuthContext.Provider value={{ user: data ?? null, isLoading }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function useAuthQueryInvalidation() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
