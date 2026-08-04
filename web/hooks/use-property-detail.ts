import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Property } from "@/types/feedback";

export function usePropertyDetail(propertyId: number) {
  return useQuery<Property>({
    queryKey: ["properties", "detail", propertyId],
    queryFn: () => apiFetch<Property>(`/properties/${propertyId}`),
    enabled: Number.isFinite(propertyId),
  });
}
