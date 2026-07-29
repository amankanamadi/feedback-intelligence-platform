"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { AttachmentUploader } from "@/components/feedback/AttachmentUploader";
import { useSubmitFeedbackMutation, useUploadAttachmentsMutation } from "@/hooks/use-submit-feedback";
import { detectClientContext } from "@/lib/client-context";
import { isApiError } from "@/lib/auth";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

const feedbackSchema = z.object({
  raw_text: z.string().min(1, "Please enter your feedback.").max(10_000, "Feedback is too long."),
});

type FeedbackFormValues = z.infer<typeof feedbackSchema>;

export function FeedbackForm({ onSubmitted }: { onSubmitted: (feedback: FeedbackUser | FeedbackAdmin) => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const submitMutation = useSubmitFeedbackMutation();
  const uploadMutation = useUploadAttachmentsMutation();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FeedbackFormValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: { raw_text: "" },
  });

  const isSubmitting = submitMutation.isPending || uploadMutation.isPending;

  const onSubmit = async (values: FeedbackFormValues) => {
    try {
      const feedback = await submitMutation.mutateAsync({
        raw_text: values.raw_text,
        source: "Web Form",
        ...detectClientContext(),
      });

      if (files.length > 0) {
        await uploadMutation.mutateAsync({ feedbackId: feedback.id, files });
      }

      reset();
      setFiles([]);
      onSubmitted(feedback);
    } catch (error) {
      toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="raw_text">What&apos;s on your mind?</Label>
        <Textarea
          id="raw_text"
          rows={8}
          placeholder="Share an idea, report a bug, or tell us how we're doing..."
          {...register("raw_text")}
        />
        {errors.raw_text && (
          <p className="text-sm text-destructive" role="alert">
            {errors.raw_text.message}
          </p>
        )}
      </div>

      <AttachmentUploader files={files} onChange={setFiles} />

      <Button type="submit" className="w-fit" isLoading={isSubmitting}>
        Submit feedback
      </Button>
    </form>
  );
}
