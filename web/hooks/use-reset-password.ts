import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

export function useResetPasswordMutation() {
  return useMutation({
    mutationFn: (payload: { token: string; new_password: string }) =>
      apiFetch<void>("/auth/reset-password", { method: "POST", body: JSON.stringify(payload) }),
  });
}
