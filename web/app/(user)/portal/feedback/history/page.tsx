import { MessageSquareHeart } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";

export default function FeedbackHistoryPage() {
  return (
    <EmptyState
      icon={<MessageSquareHeart className="size-10" aria-hidden="true" />}
      title="Your feedback history is coming soon"
      description="This page will list the feedback you've submitted, its status, and any responses from our team."
      className="flex-1"
    />
  );
}
