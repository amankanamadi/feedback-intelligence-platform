import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackAdmin, FeedbackDecisionCreate, FeedbackUser } from "@/types/feedback";

export function useSubmitFeedbackDecisionMutation(feedbackId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: FeedbackDecisionCreate) =>
      apiFetch<FeedbackUser | FeedbackAdmin>(`/feedback/${feedbackId}/decision`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["feedback", "detail", feedbackId], updated);
      // Broad "feedback"-prefixed invalidate - a decision is also
      // consumed by the host queue if a host is viewing the same item.
      queryClient.invalidateQueries({ queryKey: ["feedback"] });
    },
  });
}
