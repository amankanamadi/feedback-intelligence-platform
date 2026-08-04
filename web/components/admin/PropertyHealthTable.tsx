import { Building2 } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PropertyHealth } from "@/types/analytics";

// Two dimensions worth comparing at once (score + volume) reads more
// clearly as a table than forced into a bar chart - per the dataviz
// skill, a chart earns its place only when the shape of change matters
// more than the exact values, which isn't the case for a ranked list like
// this.
export function PropertyHealthTable({ data }: { data: PropertyHealth[] }) {
  if (data.length === 0) {
    return (
      <EmptyState
        icon={<Building2 className="size-10" aria-hidden="true" />}
        title="No property data yet"
        description="Health scores will show up here once properties have feedback."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Property</TableHead>
          <TableHead>City</TableHead>
          <TableHead>Health score</TableHead>
          <TableHead>Feedback</TableHead>
          <TableHead>Open maintenance</TableHead>
          <TableHead>SLA breached</TableHead>
          <TableHead>Avg. cleanliness</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.property_id}>
            <TableCell className="text-foreground">{row.property_name}</TableCell>
            <TableCell className="text-muted-foreground">{row.city}</TableCell>
            <TableCell className={row.health_score >= 0 ? "font-medium text-success" : "font-medium text-destructive"}>
              {row.health_score}
            </TableCell>
            <TableCell className="text-muted-foreground">{row.feedback_count}</TableCell>
            <TableCell className="text-muted-foreground">{row.open_maintenance_count}</TableCell>
            <TableCell className="text-muted-foreground">{row.sla_breached_count}</TableCell>
            <TableCell className="text-muted-foreground">{row.avg_cleanliness_rating ?? "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
