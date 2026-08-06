"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { AttachmentUploader } from "@/components/feedback/AttachmentUploader";
import { useBookingLookupMutation } from "@/hooks/use-booking-lookup";
import { useSubmitFeedbackMutation, useUploadAttachmentsMutation } from "@/hooks/use-submit-feedback";
import { useProperties } from "@/hooks/use-properties";
import { useIsGuest } from "@/hooks/use-is-guest";
import { detectClientContext } from "@/lib/client-context";
import { isApiError } from "@/lib/auth";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

const feedbackSchema = z.object({
  raw_text: z.string().min(1, "Please enter your feedback.").max(10_000, "Feedback is too long."),
  property_id: z.string().optional(),
  confirmation_code: z.string().optional(),
});

type FeedbackFormValues = z.infer<typeof feedbackSchema>;

export function FeedbackForm({
  onSubmitted,
  placeholder = "Share a review, report an issue with your stay or listing, or tell us how we're doing...",
}: {
  onSubmitted: (feedback: FeedbackUser | FeedbackAdmin) => void;
  placeholder?: string;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const submitMutation = useSubmitFeedbackMutation();
  const uploadMutation = useUploadAttachmentsMutation();
  const lookupMutation = useBookingLookupMutation();
  const propertiesQuery = useProperties();
  const isGuest = useIsGuest();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FeedbackFormValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: { raw_text: "", property_id: "", confirmation_code: "" },
  });

  const isSubmitting = submitMutation.isPending || uploadMutation.isPending || lookupMutation.isPending;

  const onSubmit = async (values: FeedbackFormValues) => {
    try {
      // Optional, guest-only: a booking is the only way a guest can tie
      // general feedback to a property (enforced server-side too) - left
      // blank, this behaves exactly like before (no property reference
      // at all).
      let bookingId: number | undefined;
      if (isGuest && values.confirmation_code?.trim()) {
        const booking = await lookupMutation.mutateAsync(values.confirmation_code);
        bookingId = booking.id;
      }

      const feedback = await submitMutation.mutateAsync({
        raw_text: values.raw_text,
        source: "Website",
        property_id: values.property_id ? Number(values.property_id) : undefined,
        booking_id: bookingId,
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
        <Textarea id="raw_text" rows={8} placeholder={placeholder} {...register("raw_text")} />
        {errors.raw_text && (
          <p className="text-sm text-destructive" role="alert">
            {errors.raw_text.message}
          </p>
        )}
      </div>

      {isGuest ? (
        // A guest can only ever reference a property through a real
        // booking (enforced server-side too), so this takes a
        // confirmation code instead of a free listing picker - optional,
        // resolved to a real booking at submit time, and left blank
        // behaves exactly as if the field didn't exist. Rating a
        // completed stay still goes through the dedicated Checkout
        // Feedback flow, not here.
        <div className="flex flex-col gap-2">
          <Label htmlFor="confirmation_code">Booking confirmation code (optional)</Label>
          <Input
            id="confirmation_code"
            placeholder="e.g. ABC12345"
            {...register("confirmation_code")}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <Label htmlFor="property_id">Which listing is this about? (optional)</Label>
          <select
            id="property_id"
            {...register("property_id")}
            className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground"
          >
            <option value="">Not tied to a specific listing</option>
            {propertiesQuery.data?.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name} — {property.city}, {property.country}
              </option>
            ))}
          </select>
        </div>
      )}

      <AttachmentUploader files={files} onChange={setFiles} />

      <Button type="submit" className="w-fit" isLoading={isSubmitting}>
        Submit feedback
      </Button>
    </form>
  );
}
