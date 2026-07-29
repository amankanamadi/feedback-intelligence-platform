"use client";

import Link from "next/link";
import { MessageSquareHeart } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ListSkeleton } from "@/components/shared/LoadingSkeletons";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useFeedbackList } from "@/hooks/use-feedback-list";
import { formatDate } from "@/lib/format";
import type { FeedbackUser } from "@/types/feedback";

export function FeedbackListUser() {
  const query = useFeedbackList({ limit: 100 });

  return (
    <DataState
      query={query}
      skeleton={<ListSkeleton />}
      empty={(items) => items.length === 0}
      emptyState={
        <EmptyState
          icon={<MessageSquareHeart className="size-10" aria-hidden="true" />}
          title="No feedback yet"
          description="Feedback you submit will show up here so you can track its status."
        />
      }
    >
      {(items) => (
        <ul className="flex flex-col gap-3">
          {(items as FeedbackUser[]).map((item) => (
            <li key={item.id}>
              <Link
                href={`/app/feedback/${item.id}`}
                className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4 transition-colors hover:bg-muted"
              >
                <div className="flex items-start justify-between gap-4">
                  <p className="line-clamp-2 text-sm text-foreground">{item.raw_text}</p>
                  <StatusBadge status={item.status} />
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{formatDate(item.created_at)}</span>
                  {item.admin_response && <span className="text-primary">Response received</span>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </DataState>
  );
}
