"use client";

import { FeedbackListAdmin } from "@/components/feedback/FeedbackListAdmin";
import { FeedbackListUser } from "@/components/feedback/FeedbackListUser";
import { useAuth } from "@/lib/auth";

export default function FeedbackPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{isAdmin ? "All Feedback" : "My Feedback"}</h1>
        <p className="text-muted-foreground">
          {isAdmin ? "Review, categorize, and respond to incoming feedback." : "Track the status of feedback you've submitted."}
        </p>
      </div>
      {isAdmin ? <FeedbackListAdmin /> : <FeedbackListUser />}
    </div>
  );
}
