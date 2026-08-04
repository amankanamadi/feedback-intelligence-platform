"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useUpdateFeedbackMutation } from "@/hooks/use-update-feedback";
import { isApiError } from "@/lib/auth";
import { STATUS_OPTIONS, type FeedbackHostRead, type FeedbackStatus } from "@/types/feedback";

type RespondFormValues = {
  status: FeedbackStatus;
  admin_response: string;
};

export function RespondDialog({ feedback }: { feedback: FeedbackHostRead }) {
  const [open, setOpen] = useState(false);
  const updateMutation = useUpdateFeedbackMutation(feedback.id);

  const { register, handleSubmit, reset } = useForm<RespondFormValues>({
    defaultValues: { status: feedback.status, admin_response: feedback.admin_response ?? "" },
  });

  const onOpenChange = (next: boolean) => {
    setOpen(next);
    if (next) reset({ status: feedback.status, admin_response: feedback.admin_response ?? "" });
  };

  const onSubmit = (values: RespondFormValues) => {
    // Only status/admin_response - a host's PATCH is restricted to these
    // two fields server-side; sending anything else would 403.
    updateMutation.mutate(
      { status: values.status, admin_response: values.admin_response },
      {
        onSuccess: () => {
          toast.success("Response sent.");
          setOpen(false);
        },
        onError: (error) => toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Respond
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Respond to feedback</DialogTitle>
            <DialogDescription>{feedback.raw_text}</DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            <Label htmlFor="status">Status</Label>
            <select
              id="status"
              {...register("status")}
              className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground"
            >
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="admin_response">Your response</Label>
            <Textarea id="admin_response" rows={5} {...register("admin_response")} />
          </div>

          <DialogFooter>
            <Button type="submit" isLoading={updateMutation.isPending}>
              Send response
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
