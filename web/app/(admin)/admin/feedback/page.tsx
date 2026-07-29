import { Inbox } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function AdminFeedbackPage() {
  return (
    <EmptyState
      icon={<Inbox className="size-10" aria-hidden="true" />}
      title="Feedback management coming soon"
      description="This page will list all feedback with filters, search, AI insights, and editable status/priority/tags/responses."
    />
  );
}
