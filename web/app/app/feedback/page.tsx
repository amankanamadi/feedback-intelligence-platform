import { Inbox } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function FeedbackPage() {
  return (
    <EmptyState
      icon={<Inbox className="size-10" aria-hidden="true" />}
      title="Feedback list coming soon"
      description="This page will list feedback - your own submissions if you're a member, or everyone's with filters, search, and AI insights if you're an admin."
    />
  );
}
