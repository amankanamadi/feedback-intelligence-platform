"use client";

import { useParams } from "next/navigation";
import { MessageSquareHeart } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { DetailSkeleton } from "@/components/shared/LoadingSkeletons";
import { EmptyState } from "@/components/shared/EmptyState";
import { FeedbackDetailAdmin } from "@/components/feedback/FeedbackDetailAdmin";
import { FeedbackDetailUser } from "@/components/feedback/FeedbackDetailUser";
import { useFeedbackDetail } from "@/hooks/use-feedback-detail";
import { useAuth } from "@/lib/auth";
import type { FeedbackAdmin, FeedbackUser } from "@/types/feedback";

export default function FeedbackDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { user } = useAuth();
  const query = useFeedbackDetail(id);

  if (!Number.isFinite(id)) {
    return (
      <EmptyState
        icon={<MessageSquareHeart className="size-10" aria-hidden="true" />}
        title="Feedback not found"
        description="That doesn't look like a valid feedback link."
      />
    );
  }

  return (
    <DataState query={query} skeleton={<DetailSkeleton />}>
      {(feedback) =>
        user?.role === "ADMIN" ? (
          <FeedbackDetailAdmin feedback={feedback as FeedbackAdmin} />
        ) : (
          <FeedbackDetailUser feedback={feedback as FeedbackUser} />
        )
      }
    </DataState>
  );
}
