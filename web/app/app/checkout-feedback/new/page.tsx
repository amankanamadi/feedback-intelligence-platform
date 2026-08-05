"use client";

import { useState } from "react";
import { StayFeedbackForm } from "@/components/feedback/StayFeedbackForm";
import { SubmissionSuccess } from "@/components/feedback/SubmissionSuccess";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

export default function NewCheckoutFeedbackPage() {
  const [submitted, setSubmitted] = useState<FeedbackUser | FeedbackAdmin | null>(null);

  if (submitted) {
    return <SubmissionSuccess feedback={submitted} onSubmitAnother={() => setSubmitted(null)} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Checkout Feedback</h1>
        <p className="text-muted-foreground">
          Look up your stay by confirmation code to rate it or report an issue - separate from general feedback.
        </p>
      </div>
      <div className="max-w-2xl">
        <StayFeedbackForm onSubmitted={setSubmitted} />
      </div>
    </div>
  );
}
