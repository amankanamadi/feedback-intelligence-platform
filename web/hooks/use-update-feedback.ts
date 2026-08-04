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
      // Broad "feedback"-prefixed invalidate, not just ["feedback","list"] -
      // this PATCH is also consumed by the host queue
      // (["feedback","host-queue",...]), which wouldn't match a
      // ["feedback","list"]-scoped invalidate under react-query's default
      // prefix matching.
      queryClient.invalidateQueries({ queryKey: ["feedback"] });
    },
  });
}
