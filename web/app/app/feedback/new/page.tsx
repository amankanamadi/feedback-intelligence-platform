import { MessageSquarePlus } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function NewFeedbackPage() {
  return (
    <EmptyState
      icon={<MessageSquarePlus className="size-10" aria-hidden="true" />}
      title="Feedback submission form coming soon"
      description="This page will let you submit new feedback and see an instant acknowledgement."
    />
  );
}
