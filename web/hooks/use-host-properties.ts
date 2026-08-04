import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { Property } from "@/types/feedback";

export function useHostProperties() {
  const { user } = useAuth();
  return useQuery<Property[]>({
    queryKey: ["properties", "host", user?.id],
    queryFn: () => apiFetch<Property[]>(`/properties?host_id=${user!.id}`),
    enabled: !!user?.id,
  });
}
