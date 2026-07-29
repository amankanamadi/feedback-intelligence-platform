"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PriorityBadge, SentimentBadge, StatusBadge } from "@/components/shared/StatusBadge";
import { useUpdateFeedbackMutation } from "@/hooks/use-update-feedback";
import { API_BASE_URL } from "@/lib/api-client";
import { isApiError } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { PRIORITY_OPTIONS, STATUS_OPTIONS, type FeedbackAdmin, type FeedbackStatus, type Priority } from "@/types/feedback";

type EditFormValues = {
  status: FeedbackStatus;
  priority: Priority | "";
  tags: string;
  internal_notes: string;
  admin_response: string;
};

export function FeedbackDetailAdmin({ feedback }: { feedback: FeedbackAdmin }) {
  const updateMutation = useUpdateFeedbackMutation(feedback.id);

  const { register, handleSubmit, reset, formState } = useForm<EditFormValues>({
    defaultValues: {
      status: feedback.status,
      priority: feedback.priority ?? "",
      tags: feedback.tags.join(", "),
      internal_notes: feedback.internal_notes ?? "",
      admin_response: feedback.admin_response ?? "",
    },
  });

  // Keep the edit form in sync if the underlying feedback changes (e.g.
  // after a successful save re-populates the query cache).
  useEffect(() => {
    reset({
      status: feedback.status,
      priority: feedback.priority ?? "",
      tags: feedback.tags.join(", "),
      internal_notes: feedback.internal_notes ?? "",
      admin_response: feedback.admin_response ?? "",
    });
  }, [feedback, reset]);

  const onSubmit = (values: EditFormValues) => {
    updateMutation.mutate(
      {
        status: values.status,
        priority: values.priority || undefined,
        tags: values.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        internal_notes: values.internal_notes,
        admin_response: values.admin_response,
      },
      {
        onSuccess: () => toast.success("Feedback updated."),
        onError: (error) => toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
      }
    );
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Feedback #{feedback.id}</CardTitle>
              <StatusBadge status={feedback.status} />
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="whitespace-pre-wrap text-sm text-foreground">{feedback.raw_text}</p>
            <dl className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              <div>
                <dt>Submitted</dt>
                <dd className="text-foreground">{formatDateTime(feedback.created_at)}</dd>
              </div>
              <div>
                <dt>Submitter</dt>
                <dd className="text-foreground">
                  {feedback.name ?? feedback.email ?? (feedback.user_id ? `User #${feedback.user_id}` : "Anonymous/import")}
                </dd>
              </div>
              {feedback.source && (
                <div>
                  <dt>Source</dt>
                  <dd className="text-foreground">{feedback.source}</dd>
                </div>
              )}
              {feedback.product && (
                <div>
                  <dt>Product</dt>
                  <dd className="text-foreground">{feedback.product}</dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI Results</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Category</dt>
                <dd className="text-foreground">{feedback.main_category ?? "Unclassified"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Subcategory</dt>
                <dd className="text-foreground">{feedback.sub_category ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Sentiment</dt>
                <dd>{feedback.sentiment ? <SentimentBadge sentiment={feedback.sentiment} /> : "-"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Confidence</dt>
                <dd className="text-foreground">{feedback.confidence !== null ? `${feedback.confidence}%` : "-"}</dd>
              </div>
            </dl>
            {feedback.summary && (
              <div>
                <p className="text-xs text-muted-foreground">Summary</p>
                <p className="text-sm text-foreground">{feedback.summary}</p>
              </div>
            )}
            {feedback.themes.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {feedback.themes.map((theme) => (
                  <Badge key={theme} variant="muted">
                    {theme}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {feedback.attachments.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Attachments</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2">
                {feedback.attachments.map((attachment) => (
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

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Manage feedback</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="status">Status</Label>
                <select
                  id="status"
                  {...register("status")}
                  className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground"
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="priority">Priority</Label>
                <select
                  id="priority"
                  {...register("priority")}
                  className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground"
                >
                  <option value="">Unset</option>
                  {PRIORITY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
                {feedback.priority && (
                  <div>
                    <PriorityBadge priority={feedback.priority} />
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="tags">Tags</Label>
              <input
                id="tags"
                {...register("tags")}
                placeholder="enterprise, sso, roadmap"
                className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <p className="text-xs text-muted-foreground">Comma-separated.</p>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="internal_notes">Internal notes</Label>
              <Textarea id="internal_notes" rows={3} {...register("internal_notes")} placeholder="Visible to admins only." />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="admin_response">Response to submitter</Label>
              <Textarea
                id="admin_response"
                rows={4}
                {...register("admin_response")}
                placeholder="This will be visible to the person who submitted this feedback."
              />
            </div>

            <Button type="submit" className="w-fit" isLoading={updateMutation.isPending} disabled={!formState.isDirty}>
              Save changes
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
