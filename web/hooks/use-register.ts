import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Me } from "@/types/auth";

export type RegisterPayload = {
  email: string;
  password: string;
  full_name?: string;
  // Self-registration only ever allows the submitter tier - staff roles
  // are provisioned out-of-band, never through this endpoint.
  role: "GUEST" | "HOST";
};

export function useRegisterMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: RegisterPayload) => apiFetch<Me>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
    },
  });
}
