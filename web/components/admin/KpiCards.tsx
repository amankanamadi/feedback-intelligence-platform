import { Card, CardContent } from "@/components/ui/card";
import type { AnalyticsSummary } from "@/types/analytics";

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-2xl font-semibold text-foreground">{value}</p>
        <p className="text-sm text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

export function KpiCards({ analytics }: { analytics: AnalyticsSummary }) {
  const tiles: { label: string; value: string | number }[] = [
    { label: "Total feedback", value: analytics.total_feedback },
    { label: "Guest satisfaction score", value: `${analytics.guest_satisfaction_score}%` },
    { label: "Safety alerts open", value: analytics.safety_alerts_open_count },
    {
      label: "Avg. resolution time",
      value: analytics.avg_resolution_time_hours !== null ? `${analytics.avg_resolution_time_hours}h` : "-",
    },
    { label: "Positive", value: `${analytics.positive_pct}%` },
    { label: "Neutral", value: `${analytics.neutral_pct}%` },
    { label: "Negative", value: `${analytics.negative_pct}%` },
    { label: "Avg. confidence", value: analytics.average_confidence !== null ? `${analytics.average_confidence}%` : "-" },
    { label: "Guest reviews", value: analytics.guest_reviews },
    { label: "Host complaints", value: analytics.host_complaints },
    { label: "Support tickets", value: analytics.support_tickets },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((tile) => (
        <StatTile key={tile.label} {...tile} />
      ))}
    </div>
  );
}
