import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetchForm } from "@/lib/api-client";
import type { FeedbackAdmin } from "@/types/feedback";

export function useBulkUploadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFetchForm<FeedbackAdmin[]>("/bulk-upload/file", formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feedback", "list"] });
    },
  });
}
