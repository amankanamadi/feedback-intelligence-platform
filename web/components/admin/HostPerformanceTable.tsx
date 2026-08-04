import type { HostPerformance } from "@/types/analytics";

export function HostPerformanceTable({ data }: { data: HostPerformance[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground">No host data yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-2 py-2">Host</th>
            <th className="px-2 py-2">Performance score</th>
            <th className="px-2 py-2">Feedback</th>
            <th className="px-2 py-2">Avg. sentiment</th>
            <th className="px-2 py-2">Open critical</th>
            <th className="px-2 py-2">SLA breached</th>
            <th className="px-2 py-2">Escalated</th>
            <th className="px-2 py-2">Avg. guest rating</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((row) => (
            <tr key={row.host_id}>
              <td className="px-2 py-2 text-foreground">{row.host_name}</td>
              <td
                className={
                  row.performance_score >= 0
                    ? "px-2 py-2 font-medium text-success"
                    : "px-2 py-2 font-medium text-destructive"
                }
              >
                {row.performance_score}
              </td>
              <td className="px-2 py-2 text-muted-foreground">{row.feedback_count}</td>
              <td
                className={
                  row.avg_sentiment_score >= 0
                    ? "px-2 py-2 font-medium text-success"
                    : "px-2 py-2 font-medium text-destructive"
                }
              >
                {row.avg_sentiment_score}
              </td>
              <td className="px-2 py-2 text-muted-foreground">{row.open_critical_count}</td>
              <td className="px-2 py-2 text-muted-foreground">{row.sla_breached_count}</td>
              <td className="px-2 py-2 text-muted-foreground">{row.escalated_count}</td>
              <td className="px-2 py-2 text-muted-foreground">{row.avg_guest_rating ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
