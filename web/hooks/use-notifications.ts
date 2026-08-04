import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { NotificationRead } from "@/types/notification";

export function useNotifications(unreadOnly = false) {
  return useQuery<NotificationRead[]>({
    queryKey: ["notifications", { unreadOnly }],
    queryFn: () => apiFetch<NotificationRead[]>(`/notifications?unread_only=${unreadOnly}&limit=20`),
    refetchInterval: 30_000,
  });
}

export function useMarkNotificationReadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => apiFetch<NotificationRead>(`/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
