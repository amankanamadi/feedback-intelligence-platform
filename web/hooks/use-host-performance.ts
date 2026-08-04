import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { HostPerformance } from "@/types/analytics";

export function useHostPerformance() {
  return useQuery<HostPerformance | null>({
    queryKey: ["analytics", "host-performance"],
    queryFn: () => apiFetch<HostPerformance | null>("/analytics/host-performance"),
  });
}
