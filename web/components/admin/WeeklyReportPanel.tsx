"use client";

import { FileClock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { useWeeklyReportMutation } from "@/hooks/use-weekly-report";
import { isApiError } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import type { FeedbackExcerpt } from "@/types/analytics";

function BulletList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-sm font-medium text-foreground">{label}</p>
      <ul className="list-disc pl-5 text-sm text-muted-foreground">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function ExcerptList({ label, items }: { label: string; items: FeedbackExcerpt[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-sm font-medium text-foreground">{label}</p>
      <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
        {items.map((item) => {
          const tags = [item.main_category, item.sentiment, item.priority].filter(Boolean).join(" / ");
          return (
            <li key={item.id}>
              {tags && <span className="text-xs text-muted-foreground">[{tags}]</span>} {item.raw_text}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function WeeklyReportPanel() {
  const reportMutation = useWeeklyReportMutation();

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-base">Weekly executive summary</CardTitle>
        <Button size="sm" onClick={() => reportMutation.mutate()} isLoading={reportMutation.isPending}>
          Generate report
        </Button>
      </CardHeader>
      <CardContent>
        {reportMutation.isError && (
          <p className="text-sm text-destructive">
            {isApiError(reportMutation.error) ? reportMutation.error.message : "Something went wrong. Please try again."}
          </p>
        )}
        {!reportMutation.data && !reportMutation.isPending && !reportMutation.isError && (
          <EmptyState
            icon={<FileClock className="size-10" aria-hidden="true" />}
            title="No report generated yet"
            description="Click Generate report to have AI write a summary of the last 7 days."
          />
        )}
        {reportMutation.data && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-muted-foreground">
              Period: {formatDate(reportMutation.data.period_start)} - {formatDate(reportMutation.data.period_end)}
            </p>
            <p className="text-sm text-foreground">{reportMutation.data.executive_summary}</p>
            <BulletList label="Key wins" items={reportMutation.data.key_wins} />
            <BulletList label="Key concerns" items={reportMutation.data.key_concerns} />
            <BulletList label="Recommended actions" items={reportMutation.data.recommended_actions} />
            <ExcerptList label="Top concerns" items={reportMutation.data.top_concerns} />
            <ExcerptList label="Positive highlights" items={reportMutation.data.positive_highlights} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
