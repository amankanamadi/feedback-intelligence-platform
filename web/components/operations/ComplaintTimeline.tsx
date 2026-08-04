import { CheckCircle2, MessageSquareReply, TriangleAlert, Send } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import type { FeedbackAdmin } from "@/types/feedback";

type TimelineEvent = {
  label: string;
  at: string;
  icon: React.ComponentType<{ className?: string }>;
};

// Derived entirely from timestamps already on the feedback record - no
// separate audit-log table exists (or is needed) for this per-case view.
function buildTimeline(feedback: FeedbackAdmin): TimelineEvent[] {
  const events: TimelineEvent[] = [{ label: "Submitted", at: feedback.created_at, icon: Send }];

  if (feedback.admin_response_at) {
    events.push({ label: "Response sent", at: feedback.admin_response_at, icon: MessageSquareReply });
  }
  if (feedback.escalated && feedback.escalated_at) {
    events.push({ label: "Escalated", at: feedback.escalated_at, icon: TriangleAlert });
  }
  if (feedback.status === "Resolved" || feedback.status === "Closed") {
    events.push({ label: feedback.status, at: feedback.updated_at, icon: CheckCircle2 });
  }

  return events.sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
}

export function ComplaintTimeline({ feedback }: { feedback: FeedbackAdmin }) {
  const events = buildTimeline(feedback);

  return (
    <ol className="flex flex-col gap-3">
      {events.map((event, index) => (
        <li key={`${event.label}-${index}`} className="flex items-start gap-3">
          <event.icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
          <div>
            <p className="text-sm font-medium text-foreground">{event.label}</p>
            <p className="text-xs text-muted-foreground">{formatDateTime(event.at)}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
