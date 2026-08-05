import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackHostRead } from "@/types/feedback";

// GET /feedback/property/{id} 403s for a host viewing a property they
// don't own - retrying that would be pointless, so disable react-query's
// default retry to fail fast rather than hammer the endpoint.
export function usePropertyFeedbackHistory(propertyId: number, options?: { enabled?: boolean }) {
  return useQuery<FeedbackHostRead[]>({
    queryKey: ["feedback", "property-history", propertyId],
    queryFn: () => apiFetch<FeedbackHostRead[]>(`/feedback/property/${propertyId}`),
    enabled: options?.enabled ?? true,
    retry: false,
  });
}
