import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackHostRead } from "@/types/feedback";

export function useHostReviews() {
  return useQuery<FeedbackHostRead[]>({
    queryKey: ["feedback", "host-reviews"],
    queryFn: () => apiFetch<FeedbackHostRead[]>("/feedback/host-reviews"),
  });
}
