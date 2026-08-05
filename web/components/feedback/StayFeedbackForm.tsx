"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { RatingInput } from "@/components/feedback/RatingInput";
import { useBookingLookupMutation } from "@/hooks/use-booking-lookup";
import { useSubmitFeedbackMutation } from "@/hooks/use-submit-feedback";
import { detectClientContext } from "@/lib/client-context";
import { isApiError } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import type { BookingRead } from "@/types/booking";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

const lookupSchema = z.object({
  confirmation_code: z.string().min(1, "Enter a confirmation code."),
});

type LookupFormValues = z.infer<typeof lookupSchema>;

// Real-life amenity/service categories - matches every other hotel/
// short-term-rental review flow. No "Overall" input here: the backend
// computes overall_rating as the rounded mean of these seven, so asking
// the guest to separately judge "overall" would just invite a value that
// could disagree with its own components.
const RATING_FIELDS = [
  "cleanliness_rating",
  "housekeeping_rating",
  "amenities_rating",
  "communication_rating",
  "checkin_rating",
  "location_rating",
  "value_rating",
] as const;

type RatingKey = (typeof RATING_FIELDS)[number];

const RATING_LABELS: Record<RatingKey, string> = {
  cleanliness_rating: "Cleanliness",
  housekeeping_rating: "Housekeeping",
  amenities_rating: "Amenities",
  communication_rating: "Communication",
  checkin_rating: "Check-in",
  location_rating: "Location",
  value_rating: "Value",
};

export function StayFeedbackForm({
  onSubmitted,
}: {
  onSubmitted: (feedback: FeedbackUser | FeedbackAdmin) => void;
}) {
  const [booking, setBooking] = useState<BookingRead | null>(null);
  const [ratings, setRatings] = useState<Record<RatingKey, number | null>>({
    cleanliness_rating: null,
    housekeeping_rating: null,
    amenities_rating: null,
    communication_rating: null,
    checkin_rating: null,
    location_rating: null,
    value_rating: null,
  });
  const [rawText, setRawText] = useState("");
  const lookupMutation = useBookingLookupMutation();
  const submitMutation = useSubmitFeedbackMutation();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LookupFormValues>({
    resolver: zodResolver(lookupSchema),
    defaultValues: { confirmation_code: "" },
  });

  const isReviewEligible = booking?.status === "Completed";
  const allRatingsSet = RATING_FIELDS.every((key) => ratings[key] !== null);

  const handleLookup = handleSubmit(async (values) => {
    try {
      const result = await lookupMutation.mutateAsync(values.confirmation_code);
      setBooking(result);
    } catch (error) {
      toast.error(isApiError(error) ? error.message : "Booking not found.");
    }
  });

  const handleSubmitStay = async () => {
    if (!booking) return;
    if (isReviewEligible && !allRatingsSet) {
      toast.error("Please rate all 7 categories.");
      return;
    }
    try {
      const feedback = await submitMutation.mutateAsync({
        raw_text: rawText,
        source: "Website",
        booking_id: booking.id,
        ...(isReviewEligible
          ? Object.fromEntries(RATING_FIELDS.map((key) => [key, ratings[key] as number]))
          : {}),
        ...detectClientContext(),
      });
      onSubmitted(feedback);
    } catch (error) {
      toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again.");
    }
  };

  if (!booking) {
    return (
      <form onSubmit={handleLookup} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="confirmation_code">Booking confirmation code</Label>
          <Input id="confirmation_code" placeholder="e.g. ABC12345" {...register("confirmation_code")} />
          {errors.confirmation_code && (
            <p className="text-sm text-destructive" role="alert">
              {errors.confirmation_code.message}
            </p>
          )}
        </div>
        <Button type="submit" className="w-fit" isLoading={lookupMutation.isPending}>
          Look up
        </Button>
      </form>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-1 py-4 text-sm">
          <p className="font-medium text-foreground">{booking.property.name}</p>
          <p className="text-muted-foreground">
            {formatDate(booking.check_in_date)} – {formatDate(booking.check_out_date)} · {booking.status}
          </p>
        </CardContent>
      </Card>

      {isReviewEligible && (
        <div className="flex flex-col gap-4">
          {RATING_FIELDS.map((key) => (
            <RatingInput
              key={key}
              label={RATING_LABELS[key]}
              value={ratings[key]}
              onChange={(value) => setRatings((prev) => ({ ...prev, [key]: value }))}
            />
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="stay_raw_text">{isReviewEligible ? "Tell us about your stay" : "What happened?"}</Label>
        <Textarea id="stay_raw_text" rows={6} value={rawText} onChange={(e) => setRawText(e.target.value)} />
      </div>

      <div className="flex gap-3">
        <Button type="button" onClick={handleSubmitStay} isLoading={submitMutation.isPending}>
          {isReviewEligible ? "Submit review" : "Submit complaint"}
        </Button>
        <Button type="button" variant="outline" onClick={() => setBooking(null)}>
          Look up a different booking
        </Button>
      </div>
    </div>
  );
}
