import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackAdmin, FeedbackListFilters, FeedbackUser } from "@/types/feedback";

function buildQueryString(filters: FeedbackListFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function useFeedbackList(filters: FeedbackListFilters) {
  return useQuery<(FeedbackUser | FeedbackAdmin)[]>({
    queryKey: ["feedback", "list", filters],
    queryFn: () => apiFetch(`/feedback${buildQueryString(filters)}`),
  });
}
