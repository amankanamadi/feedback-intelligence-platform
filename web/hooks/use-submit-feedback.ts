import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchForm } from "@/lib/api-client";
import type { Attachment, FeedbackAdmin, FeedbackCreatePayload, FeedbackUser } from "@/types/feedback";

export function useSubmitFeedbackMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: FeedbackCreatePayload) =>
      apiFetch<FeedbackUser | FeedbackAdmin>("/feedback", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feedback", "list"] });
    },
  });
}

export function useUploadAttachmentsMutation() {
  return useMutation({
    mutationFn: ({ feedbackId, files }: { feedbackId: number; files: File[] }) => {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      return apiFetchForm<Attachment[]>(`/feedback/${feedbackId}/attachments`, formData);
    },
  });
}
