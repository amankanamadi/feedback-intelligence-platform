"use client";

import { FeedbackListAdmin } from "@/components/feedback/FeedbackListAdmin";
import { FeedbackListUser } from "@/components/feedback/FeedbackListUser";
import { useIsStaff } from "@/hooks/use-is-staff";

export default function FeedbackPage() {
  const isStaff = useIsStaff();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{isStaff ? "All Feedback" : "My Feedback"}</h1>
        <p className="text-muted-foreground">
          {isStaff
            ? "Review, categorize, and respond to incoming guest and host feedback."
            : "Track the status of feedback you've submitted."}
        </p>
      </div>
      {isStaff ? <FeedbackListAdmin /> : <FeedbackListUser />}
    </div>
  );
}
