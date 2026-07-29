import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

export function useChangePasswordMutation() {
  return useMutation({
    mutationFn: (payload: { current_password: string; new_password: string }) =>
      apiFetch<void>("/auth/change-password", { method: "POST", body: JSON.stringify(payload) }),
  });
}
