import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

export function useFeedbackDetail(id: number) {
  return useQuery<FeedbackUser | FeedbackAdmin>({
    queryKey: ["feedback", "detail", id],
    queryFn: () => apiFetch(`/feedback/${id}`),
    enabled: Number.isFinite(id),
  });
}
