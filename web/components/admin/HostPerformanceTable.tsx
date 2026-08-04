import { Users } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { HostPerformance } from "@/types/analytics";

export function HostPerformanceTable({ data }: { data: HostPerformance[] }) {
  if (data.length === 0) {
    return (
      <EmptyState
        icon={<Users className="size-10" aria-hidden="true" />}
        title="No host data yet"
        description="Performance scores will show up here once hosts have properties with feedback."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Host</TableHead>
          <TableHead>Performance score</TableHead>
          <TableHead>Feedback</TableHead>
          <TableHead>Avg. sentiment</TableHead>
          <TableHead>Open critical</TableHead>
          <TableHead>SLA breached</TableHead>
          <TableHead>Escalated</TableHead>
          <TableHead>Avg. guest rating</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.host_id}>
            <TableCell className="text-foreground">{row.host_name}</TableCell>
            <TableCell
              className={row.performance_score >= 0 ? "font-medium text-success" : "font-medium text-destructive"}
            >
              {row.performance_score}
            </TableCell>
            <TableCell className="text-muted-foreground">{row.feedback_count}</TableCell>
            <TableCell
              className={row.avg_sentiment_score >= 0 ? "font-medium text-success" : "font-medium text-destructive"}
            >
              {row.avg_sentiment_score}
            </TableCell>
            <TableCell className="text-muted-foreground">{row.open_critical_count}</TableCell>
            <TableCell className="text-muted-foreground">{row.sla_breached_count}</TableCell>
            <TableCell className="text-muted-foreground">{row.escalated_count}</TableCell>
            <TableCell className="text-muted-foreground">{row.avg_guest_rating ?? "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
