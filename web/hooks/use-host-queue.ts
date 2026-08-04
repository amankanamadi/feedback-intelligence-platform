import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackHostRead, FeedbackStatus } from "@/types/feedback";

export function useHostQueue(status?: FeedbackStatus, unresolved?: boolean) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (unresolved) params.set("unresolved", "true");
  const query = params.toString();

  return useQuery<FeedbackHostRead[]>({
    queryKey: ["feedback", "host-queue", status, unresolved],
    queryFn: () => apiFetch<FeedbackHostRead[]>(`/feedback/host-queue${query ? `?${query}` : ""}`),
  });
}
