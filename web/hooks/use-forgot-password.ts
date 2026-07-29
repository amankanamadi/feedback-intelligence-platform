import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

type ForgotPasswordResponse = {
  detail: string;
  reset_token: string | null;
};

export function useForgotPasswordMutation() {
  return useMutation({
    mutationFn: (email: string) =>
      apiFetch<ForgotPasswordResponse>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),
  });
}
