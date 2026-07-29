import { Badge } from "@/components/ui/badge";
import type { FeedbackStatus, Priority, Sentiment } from "@/types/feedback";

const STATUS_VARIANTS: Record<FeedbackStatus, "default" | "muted" | "success" | "warning"> = {
  New: "default",
  Acknowledged: "muted",
  "In Review": "warning",
  "In Progress": "warning",
  Resolved: "success",
  Closed: "muted",
};

export function StatusBadge({ status }: { status: FeedbackStatus }) {
  return <Badge variant={STATUS_VARIANTS[status]}>{status}</Badge>;
}

const PRIORITY_VARIANTS: Record<Priority, "muted" | "default" | "warning" | "destructive"> = {
  Low: "muted",
  Medium: "default",
  High: "warning",
  Critical: "destructive",
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <Badge variant={PRIORITY_VARIANTS[priority]}>{priority}</Badge>;
}

const SENTIMENT_VARIANTS: Record<Sentiment, "success" | "muted" | "destructive"> = {
  Positive: "success",
  Neutral: "muted",
  Negative: "destructive",
};

export function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  return <Badge variant={SENTIMENT_VARIANTS[sentiment]}>{sentiment}</Badge>;
}
