import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackAdmin, FeedbackAdminUpdatePayload } from "@/types/feedback";

export function useUpdateFeedbackMutation(feedbackId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: FeedbackAdminUpdatePayload) =>
      apiFetch<FeedbackAdmin>(`/feedback/${feedbackId}`, { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["feedback", "detail", feedbackId], updated);
      queryClient.invalidateQueries({ queryKey: ["feedback", "list"] });
    },
  });
}
