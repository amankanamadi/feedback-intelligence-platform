"use client";

import { useState } from "react";
import Link from "next/link";
import { Inbox, Search } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { TableSkeleton } from "@/components/shared/LoadingSkeletons";
import { PriorityBadge, SentimentBadge, StatusBadge } from "@/components/shared/StatusBadge";
import { Input } from "@/components/ui/input";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useFeedbackList } from "@/hooks/use-feedback-list";
import { formatDate } from "@/lib/format";
import { MAIN_CATEGORY_OPTIONS, SENTIMENT_OPTIONS, type FeedbackAdmin, type MainCategory, type Sentiment } from "@/types/feedback";

export function FeedbackListAdmin() {
  const [search, setSearch] = useState("");
  const [mainCategory, setMainCategory] = useState<MainCategory | "">("");
  const [sentiment, setSentiment] = useState<Sentiment | "">("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useFeedbackList({
    limit: 200,
    search: debouncedSearch || undefined,
    main_category: mainCategory || undefined,
    sentiment: sentiment || undefined,
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            placeholder="Search feedback..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={mainCategory}
          onChange={(e) => setMainCategory(e.target.value as MainCategory | "")}
          className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground"
        >
          <option value="">All categories</option>
          {MAIN_CATEGORY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={sentiment}
          onChange={(e) => setSentiment(e.target.value as Sentiment | "")}
          className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground"
        >
          <option value="">All sentiment</option>
          {SENTIMENT_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      <DataState
        query={query}
        skeleton={<TableSkeleton />}
        empty={(items) => items.length === 0}
        emptyState={
          <EmptyState
            icon={<Inbox className="size-10" aria-hidden="true" />}
            title="No feedback matches your filters"
            description="Try adjusting or clearing the filters above."
          />
        }
      >
        {(items) => (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Feedback</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Sentiment</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(items as FeedbackAdmin[]).map((item) => (
                  <tr key={item.id} className="cursor-pointer hover:bg-muted/50">
                    <td className="max-w-xs px-4 py-3">
                      <Link href={`/app/feedback/${item.id}`} className="line-clamp-2 text-foreground hover:underline">
                        {item.raw_text}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{item.main_category ?? "-"}</td>
                    <td className="px-4 py-3">{item.sentiment ? <SentimentBadge sentiment={item.sentiment} /> : "-"}</td>
                    <td className="px-4 py-3">{item.priority ? <PriorityBadge priority={item.priority} /> : "-"}</td>
                    <td className="px-4 py-3 text-muted-foreground">{item.confidence ?? "-"}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DataState>
    </div>
  );
}
