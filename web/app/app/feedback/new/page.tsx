"use client";

import { useState } from "react";
import { FeedbackForm } from "@/components/feedback/FeedbackForm";
import { SubmissionSuccess } from "@/components/feedback/SubmissionSuccess";
import { useIsHost } from "@/hooks/use-is-host";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

const HOST_PLACEHOLDER =
  "Tell us about a recent guest, or share feedback about operations, the app, or our team...";

// Checkout feedback after a stay lives entirely on its own dedicated flow
// now (/app/checkout-feedback/new, linked from the Checkout Feedback
// dashboard) - this page is general feedback only, for everyone, so
// there's no tab/branch left to choose between "general" and "about a
// specific stay" here.
export default function NewFeedbackPage() {
  const [submitted, setSubmitted] = useState<FeedbackUser | FeedbackAdmin | null>(null);
  const isHost = useIsHost();

  if (submitted) {
    return <SubmissionSuccess feedback={submitted} onSubmitAnother={() => setSubmitted(null)} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Submit feedback</h1>
        <p className="text-muted-foreground">
          {isHost
            ? "Tell us about a recent guest, or share feedback about operations, the app, or our team."
            : "Share an idea, report a bug, or tell us how we're doing."}
        </p>
      </div>
      <div className="max-w-2xl">
        <FeedbackForm onSubmitted={setSubmitted} placeholder={isHost ? HOST_PLACEHOLDER : undefined} />
      </div>
    </div>
  );
}
