import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatDateTime } from "@/lib/format";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

export function SubmissionSuccess({
  feedback,
  onSubmitAnother,
}: {
  feedback: FeedbackUser | FeedbackAdmin;
  onSubmitAnother: () => void;
}) {
  return (
    <Card className="mx-auto w-full max-w-lg">
      <CardHeader className="items-center text-center">
        <CheckCircle2 className="size-12 text-success" aria-hidden="true" />
        <CardTitle>Feedback Submitted Successfully</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-3 rounded-md bg-muted p-4 text-sm">
          <dt className="text-muted-foreground">Feedback ID</dt>
          <dd className="text-right font-medium text-foreground">#{feedback.id}</dd>
          <dt className="text-muted-foreground">Status</dt>
          <dd className="text-right">
            <StatusBadge status={feedback.status} />
          </dd>
          <dt className="text-muted-foreground">Submitted</dt>
          <dd className="text-right font-medium text-foreground">{formatDateTime(feedback.created_at)}</dd>
        </dl>
        {feedback.acknowledgement && (
          <div className="rounded-md border border-border p-4">
            <p className="text-sm text-foreground">{feedback.acknowledgement}</p>
          </div>
        )}
        <div className="flex gap-3">
          <Button asChild className="flex-1">
            {feedback.overall_rating != null ? (
              <Link href="/app/reviews">View my reviews</Link>
            ) : (
              <Link href={`/app/feedback/${feedback.id}`}>View submitted feedback</Link>
            )}
          </Button>
          <Button variant="outline" className="flex-1" onClick={onSubmitAnother}>
            Submit another
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
