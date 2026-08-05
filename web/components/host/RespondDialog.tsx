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
import type { FeedbackHostRead } from "@/types/feedback";

type RespondFormValues = {
  admin_response: string;
};

export function RespondDialog({ feedback }: { feedback: FeedbackHostRead }) {
  const [open, setOpen] = useState(false);
  const updateMutation = useUpdateFeedbackMutation(feedback.id);

  const { register, handleSubmit, reset } = useForm<RespondFormValues>({
    defaultValues: { admin_response: feedback.admin_response ?? "" },
  });

  const onOpenChange = (next: boolean) => {
    setOpen(next);
    if (next) reset({ admin_response: feedback.admin_response ?? "" });
  };

  const onSubmit = (values: RespondFormValues) => {
    // admin_response only - status isn't a host's call (it stays with
    // AI/admin); the backend automatically advances New/Acknowledged to
    // In Progress the moment a response is sent, so there's nothing for
    // a host to pick here.
    updateMutation.mutate(
      { admin_response: values.admin_response },
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
            <Label htmlFor="admin_response">Your response</Label>
            <Textarea id="admin_response" rows={5} {...register("admin_response")} />
            <p className="text-xs text-muted-foreground">
              Status updates automatically when you respond - it isn&apos;t something you set directly.
            </p>
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
