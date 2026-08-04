"use client";

import { CategoryBarChart } from "@/components/admin/charts/CategoryBarChart";
import { ComplaintHeatmapGrid } from "@/components/admin/charts/ComplaintHeatmapGrid";
import { ConfidenceBarChart } from "@/components/admin/charts/ConfidenceBarChart";
import { FeatureRequestTrendChart } from "@/components/admin/charts/FeatureRequestTrendChart";
import { MostAffectedCitiesChart } from "@/components/admin/charts/MostAffectedCitiesChart";
import { SentimentPieChart } from "@/components/admin/charts/SentimentPieChart";
import { TopThemesChart } from "@/components/admin/charts/TopThemesChart";
import { WeeklySentimentTrendChart } from "@/components/admin/charts/WeeklySentimentTrendChart";
import { WeeklyTrendChart } from "@/components/admin/charts/WeeklyTrendChart";
import { HostPerformanceTable } from "@/components/admin/HostPerformanceTable";
import { KpiCards } from "@/components/admin/KpiCards";
import { PropertyHealthTable } from "@/components/admin/PropertyHealthTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataState } from "@/components/shared/DataState";
import { TableSkeleton } from "@/components/shared/LoadingSkeletons";
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
        <h1 className="text-2xl font-semibold text-foreground">Guest Experience Analytics</h1>
        <p className="text-muted-foreground">Sentiment, categories, properties, and trends across all guest and host feedback.</p>
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
        <ChartCard title="Weekly sentiment trend">
          <DataState query={analyticsQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(analytics) => <WeeklySentimentTrendChart data={analytics.weekly_sentiment_trend} />}
          </DataState>
        </ChartCard>
        <ChartCard title="Top themes">
          <DataState query={themesQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(themes) => <TopThemesChart data={themes} />}
          </DataState>
        </ChartCard>
        <ChartCard title="Most affected cities">
          <DataState query={analyticsQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(analytics) => <MostAffectedCitiesChart data={analytics.most_affected_cities} />}
          </DataState>
        </ChartCard>
        <ChartCard title="Feature request trend">
          <DataState query={analyticsQuery} skeleton={<Skeleton className="h-full w-full" />}>
            {(analytics) => <FeatureRequestTrendChart data={analytics.feature_request_trend} />}
          </DataState>
        </ChartCard>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Complaint heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <DataState query={analyticsQuery} skeleton={<TableSkeleton rows={4} />}>
            {(analytics) => <ComplaintHeatmapGrid data={analytics.complaint_heatmap} />}
          </DataState>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Property health</CardTitle>
          </CardHeader>
          <CardContent>
            <DataState query={analyticsQuery} skeleton={<TableSkeleton rows={4} />}>
              {(analytics) => <PropertyHealthTable data={analytics.property_health} />}
            </DataState>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Host performance</CardTitle>
          </CardHeader>
          <CardContent>
            <DataState query={analyticsQuery} skeleton={<TableSkeleton rows={4} />}>
              {(analytics) => <HostPerformanceTable data={analytics.host_performance} />}
            </DataState>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
