import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackHostRead, FeedbackStatus } from "@/types/feedback";

export function useHostQueue(status?: FeedbackStatus) {
  return useQuery<FeedbackHostRead[]>({
    queryKey: ["feedback", "host-queue", status],
    queryFn: () =>
      apiFetch<FeedbackHostRead[]>(`/feedback/host-queue${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  });
}
