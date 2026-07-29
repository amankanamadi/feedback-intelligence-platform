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
    { label: "Positive", value: `${analytics.positive_pct}%` },
    { label: "Neutral", value: `${analytics.neutral_pct}%` },
    { label: "Negative", value: `${analytics.negative_pct}%` },
    { label: "Incidents", value: analytics.incidents },
    { label: "Service requests", value: analytics.service_requests },
    { label: "General feedback", value: analytics.general_feedback },
    { label: "Avg. confidence", value: analytics.average_confidence !== null ? `${analytics.average_confidence}%` : "-" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((tile) => (
        <StatTile key={tile.label} {...tile} />
      ))}
    </div>
  );
}
