import type { PropertyHealth } from "@/types/analytics";

// Two dimensions worth comparing at once (score + volume) reads more
// clearly as a table than forced into a bar chart - per the dataviz
// skill, a chart earns its place only when the shape of change matters
// more than the exact values, which isn't the case for a ranked list like
// this.
export function PropertyHealthTable({ data }: { data: PropertyHealth[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground">No property data yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-2 py-2">Property</th>
            <th className="px-2 py-2">City</th>
            <th className="px-2 py-2">Health score</th>
            <th className="px-2 py-2">Feedback</th>
            <th className="px-2 py-2">Open maintenance</th>
            <th className="px-2 py-2">SLA breached</th>
            <th className="px-2 py-2">Avg. cleanliness</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((row) => (
            <tr key={row.property_id}>
              <td className="px-2 py-2 text-foreground">{row.property_name}</td>
              <td className="px-2 py-2 text-muted-foreground">{row.city}</td>
              <td
                className={
                  row.health_score >= 0 ? "px-2 py-2 font-medium text-success" : "px-2 py-2 font-medium text-destructive"
                }
              >
                {row.health_score}
              </td>
              <td className="px-2 py-2 text-muted-foreground">{row.feedback_count}</td>
              <td className="px-2 py-2 text-muted-foreground">{row.open_maintenance_count}</td>
              <td className="px-2 py-2 text-muted-foreground">{row.sla_breached_count}</td>
              <td className="px-2 py-2 text-muted-foreground">{row.avg_cleanliness_rating ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
