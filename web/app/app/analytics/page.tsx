"use client";

import { CategoryBarChart } from "@/components/admin/charts/CategoryBarChart";
import { ConfidenceBarChart } from "@/components/admin/charts/ConfidenceBarChart";
import { SentimentPieChart } from "@/components/admin/charts/SentimentPieChart";
import { TopThemesChart } from "@/components/admin/charts/TopThemesChart";
import { WeeklyTrendChart } from "@/components/admin/charts/WeeklyTrendChart";
import { KpiCards } from "@/components/admin/KpiCards";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataState } from "@/components/shared/DataState";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalytics } from "@/hooks/use-analytics";
import { useThemes } from "@/hooks/use-themes";

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="h-64">{children}</CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const analyticsQuery = useAnalytics();
  const themesQuery = useThemes(10);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Analytics</h1>
        <p className="text-muted-foreground">Sentiment, categories, and trends across all feedback.</p>
      </div>

      <DataState query={analyticsQuery} skeleton={<Skeleton className="h-24 w-full" />}>
        {(analytics) => <KpiCards analytics={analytics} />}
      </DataState>

      <div className="grid gap-4 md:grid-cols-2">
        <ChartCard title="Sentiment breakdown">
          <DataState query={analyticsQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(analytics) => <SentimentPieChart data={analytics.sentiment_breakdown} />}
          </DataState>
        </ChartCard>
        <ChartCard title="Category breakdown">
          <DataState query={analyticsQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(analytics) => <CategoryBarChart data={analytics.category_breakdown} />}
          </DataState>
        </ChartCard>
        <ChartCard title="Confidence distribution">
          <DataState query={analyticsQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(analytics) => <ConfidenceBarChart data={analytics.confidence_distribution} />}
          </DataState>
        </ChartCard>
        <ChartCard title="Weekly trend">
          <DataState query={analyticsQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(analytics) => <WeeklyTrendChart data={analytics.weekly_trend} />}
          </DataState>
        </ChartCard>
        <ChartCard title="Top themes">
          <DataState query={themesQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(themes) => <TopThemesChart data={themes} />}
          </DataState>
        </ChartCard>
      </div>
    </div>
  );
}
