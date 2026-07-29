import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { AnalyticsSummary } from "@/types/analytics";

export function useAnalytics() {
  return useQuery<AnalyticsSummary>({
    queryKey: ["analytics"],
    queryFn: () => apiFetch<AnalyticsSummary>("/analytics"),
  });
}
