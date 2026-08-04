"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useSubmitFeedbackDecisionMutation } from "@/hooks/use-feedback-decision";
import { API_BASE_URL } from "@/lib/api-client";
import { isApiError } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import type { FeedbackUser } from "@/types/feedback";

// Destructures only the fields FeedbackUser actually has - never spreads
// the object into JSX, so a stray backend field can't leak through even
// if the API ever over-returns for a USER-role caller.
export function FeedbackDetailUser({ feedback }: { feedback: FeedbackUser }) {
  const {
    id,
    raw_text,
    status,
    acknowledgement,
    admin_response,
    admin_response_at,
    guest_decision,
    attachments,
    property_name,
    property_city,
    created_at,
    updated_at,
  } = feedback;

  const [confirmReject, setConfirmReject] = useState(false);
  const decisionMutation = useSubmitFeedbackDecisionMutation(id);

  const handleDecision = (decision: "Accepted" | "Rejected") => {
    decisionMutation.mutate(
      { decision },
      {
        onSuccess: () => setConfirmReject(false),
        onError: (error) => toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
      }
    );
  };

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
            {property_name && (
              <div>
                <dt>Listing</dt>
                <dd className="text-foreground">
                  {property_name}
                  {property_city ? ` — ${property_city}` : ""}
                </dd>
              </div>
            )}
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
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm text-foreground">{admin_response}</p>
            {admin_response_at && <p className="text-xs text-muted-foreground">{formatDateTime(admin_response_at)}</p>}

            {guest_decision ? (
              <Badge variant={guest_decision === "Accepted" ? "success" : "destructive"} className="w-fit">
                You {guest_decision.toLowerCase()} this resolution
              </Badge>
            ) : (
              <div className="flex gap-2 pt-1">
                <Button
                  size="sm"
                  isLoading={decisionMutation.isPending && decisionMutation.variables?.decision === "Accepted"}
                  onClick={() => handleDecision("Accepted")}
                >
                  Accept resolution
                </Button>
                <Button size="sm" variant="outline" onClick={() => setConfirmReject(true)}>
                  Reject resolution
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog open={confirmReject} onOpenChange={setConfirmReject}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject this resolution?</DialogTitle>
            <DialogDescription>
              This escalates your feedback to a manager for further review. This can&apos;t be undone once submitted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="destructive" isLoading={decisionMutation.isPending} onClick={() => handleDecision("Rejected")}>
              Confirm reject
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
