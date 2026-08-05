"use client";

import Link from "next/link";
import { MessageSquareHeart, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ListSkeleton } from "@/components/shared/LoadingSkeletons";
import { useFeedbackList } from "@/hooks/use-feedback-list";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { FeedbackUser } from "@/types/feedback";

const CATEGORY_LABELS = {
  cleanliness_rating: "Cleanliness",
  housekeeping_rating: "Housekeeping",
  amenities_rating: "Amenities",
  communication_rating: "Communication",
  checkin_rating: "Check-in",
  location_rating: "Location",
  value_rating: "Value",
} as const;

type CategoryKey = keyof typeof CATEGORY_LABELS;

function Stars({ value, size = "size-4" }: { value: number; size?: string }) {
  return (
    <div className="flex gap-0.5" aria-label={`${value} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={cn(size, n <= value ? "fill-amber-400 text-amber-400" : "text-muted-foreground")}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

function ReviewCard({ review }: { review: FeedbackUser }) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-base">{review.property_name ?? "General feedback"}</CardTitle>
          <p className="text-xs text-muted-foreground">{formatDate(review.created_at)}</p>
        </div>
        {review.overall_rating != null && (
          <div className="flex items-center gap-2">
            <Stars value={review.overall_rating} size="size-5" />
            <span className="text-sm font-medium text-foreground">{review.overall_rating}/5</span>
          </div>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-foreground">{review.raw_text}</p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
          {(Object.keys(CATEGORY_LABELS) as CategoryKey[]).map((key) => {
            const value = review[key];
            if (value == null) return null;
            return (
              <div key={key} className="flex items-center justify-between gap-2 text-sm">
                <span className="text-muted-foreground">{CATEGORY_LABELS[key]}</span>
                <Stars value={value} />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default function MyReviewsPage() {
  const query = useFeedbackList({ main_category: "Guest Review" });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">My Reviews</h1>
        <p className="text-muted-foreground">Reviews you&apos;ve left after checking out of a stay.</p>
      </div>

      <DataState
        query={query}
        skeleton={<ListSkeleton rows={3} />}
        empty={(data) => data.length === 0}
        emptyState={
          <EmptyState
            icon={<MessageSquareHeart className="size-10" aria-hidden="true" />}
            title="No reviews yet"
            description="Once you check out of a completed stay, you can rate it here."
            action={
              <Button asChild size="sm">
                <Link href="/app/feedback/new">Submit a review</Link>
              </Button>
            }
          />
        }
      >
        {(items) => (
          <div className="flex flex-col gap-4">
            {(items as FeedbackUser[]).map((review) => (
              <ReviewCard key={review.id} review={review} />
            ))}
          </div>
        )}
      </DataState>
    </div>
  );
}
