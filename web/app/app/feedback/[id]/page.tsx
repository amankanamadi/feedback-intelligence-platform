import { MessageSquareHeart } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function FeedbackDetailPage() {
  return (
    <EmptyState
      icon={<MessageSquareHeart className="size-10" aria-hidden="true" />}
      title="Feedback detail coming soon"
      description="This page will show status/acknowledgement/admin response - and for admins, full AI results with editable status/priority/tags/response."
    />
  );
}
