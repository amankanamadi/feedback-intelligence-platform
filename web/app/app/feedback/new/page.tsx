"use client";

import { useState } from "react";
import { FeedbackForm } from "@/components/feedback/FeedbackForm";
import { SubmissionSuccess } from "@/components/feedback/SubmissionSuccess";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

export default function NewFeedbackPage() {
  const [submitted, setSubmitted] = useState<FeedbackUser | FeedbackAdmin | null>(null);

  if (submitted) {
    return <SubmissionSuccess feedback={submitted} onSubmitAnother={() => setSubmitted(null)} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Submit feedback</h1>
        <p className="text-muted-foreground">Share an idea, report a bug, or tell us how we&apos;re doing.</p>
      </div>
      <div className="max-w-2xl">
        <FeedbackForm onSubmitted={setSubmitted} />
      </div>
    </div>
  );
}
