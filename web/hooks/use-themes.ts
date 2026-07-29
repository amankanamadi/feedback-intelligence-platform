import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { ThemeFrequency } from "@/types/analytics";

export function useThemes(limit: number = 10) {
  return useQuery<ThemeFrequency[]>({
    queryKey: ["themes", limit],
    queryFn: () => apiFetch<ThemeFrequency[]>(`/themes?limit=${limit}`),
  });
}
