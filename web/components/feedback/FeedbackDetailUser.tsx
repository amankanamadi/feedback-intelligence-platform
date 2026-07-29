import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { API_BASE_URL } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import type { FeedbackUser } from "@/types/feedback";

// Destructures only the fields FeedbackUser actually has - never spreads
// the object into JSX, so a stray backend field can't leak through even
// if the API ever over-returns for a USER-role caller.
export function FeedbackDetailUser({ feedback }: { feedback: FeedbackUser }) {
  const { id, raw_text, status, acknowledgement, admin_response, admin_response_at, attachments, created_at, updated_at } =
    feedback;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Feedback #{id}</CardTitle>
            <StatusBadge status={status} />
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="whitespace-pre-wrap text-sm text-foreground">{raw_text}</p>
          <dl className="grid grid-cols-2 gap-2 text-xs text-muted-foreground sm:grid-cols-4">
            <div>
              <dt>Submitted</dt>
              <dd className="text-foreground">{formatDateTime(created_at)}</dd>
            </div>
            <div>
              <dt>Last updated</dt>
              <dd className="text-foreground">{formatDateTime(updated_at)}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {acknowledgement && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Acknowledgement</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground">{acknowledgement}</p>
          </CardContent>
        </Card>
      )}

      {admin_response && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Response from our team</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            <p className="text-sm text-foreground">{admin_response}</p>
            {admin_response_at && <p className="text-xs text-muted-foreground">{formatDateTime(admin_response_at)}</p>}
          </CardContent>
        </Card>
      )}

      {attachments.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Attachments</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-2">
              {attachments.map((attachment) => (
                <li key={attachment.id} className="text-sm">
                  <a
                    href={`${API_BASE_URL}/attachments/${attachment.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    {attachment.filename}
                  </a>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
