import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Property } from "@/types/feedback";

export function useProperties(search?: string) {
  return useQuery<Property[]>({
    queryKey: ["properties", search],
    queryFn: () => apiFetch<Property[]>(`/properties${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  });
}
