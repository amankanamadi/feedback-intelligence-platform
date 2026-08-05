"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FeedbackForm } from "@/components/feedback/FeedbackForm";
import { StayFeedbackForm } from "@/components/feedback/StayFeedbackForm";
import { SubmissionSuccess } from "@/components/feedback/SubmissionSuccess";
import { useIsHost } from "@/hooks/use-is-host";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

const HOST_PLACEHOLDER =
  "Tell us about a recent guest, or share feedback about operations, the app, or our team...";

export default function NewFeedbackPage() {
  const [submitted, setSubmitted] = useState<FeedbackUser | FeedbackAdmin | null>(null);
  const isHost = useIsHost();

  if (submitted) {
    return <SubmissionSuccess feedback={submitted} onSubmitAnother={() => setSubmitted(null)} />;
  }

  // A host doesn't "leave a property" the way a guest does, so the
  // booking-lookup stay-review flow (About a specific stay) doesn't apply
  // to them - they get the general form only, framed for reporting on a
  // recent guest or on operations/app/team issues instead.
  if (isHost) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Submit feedback</h1>
          <p className="text-muted-foreground">Tell us about a recent guest, or share feedback about operations, the app, or our team.</p>
        </div>
        <div className="max-w-2xl">
          <FeedbackForm onSubmitted={setSubmitted} placeholder={HOST_PLACEHOLDER} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Submit feedback</h1>
        <p className="text-muted-foreground">Share an idea, report a bug, or tell us how we&apos;re doing.</p>
      </div>
      <div className="max-w-2xl">
        <Tabs defaultValue="general">
          <TabsList>
            <TabsTrigger value="general">General feedback</TabsTrigger>
            <TabsTrigger value="stay">About a specific stay</TabsTrigger>
          </TabsList>
          <TabsContent value="general">
            <FeedbackForm onSubmitted={setSubmitted} />
          </TabsContent>
          <TabsContent value="stay">
            <StayFeedbackForm onSubmitted={setSubmitted} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
