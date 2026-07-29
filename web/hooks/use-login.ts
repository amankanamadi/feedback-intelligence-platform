import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Me } from "@/types/auth";

export type LoginPayload = {
  email: string;
  password: string;
  remember_me: boolean;
};

export function useLoginMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: LoginPayload) => apiFetch<Me>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
    },
  });
}
