import { Map as MapIcon } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CONFIDENCE_SEQUENTIAL } from "@/lib/chart-colors";
import type { HeatmapCell } from "@/types/analytics";

// A real Chart.js heatmap needs a matrix-controller plugin this project
// deliberately doesn't depend on (chart-based/no-new-library was the
// established decision for maps/heatmaps) - a plain HTML grid, shaded
// with the existing sequential palette by relative intensity, gets the
// same "where are the hot spots" read without a new dependency.
export function ComplaintHeatmapGrid({ data }: { data: HeatmapCell[] }) {
  if (data.length === 0) {
    return (
      <EmptyState
        icon={<MapIcon className="size-10" aria-hidden="true" />}
        title="No complaint data yet"
        description="The heatmap fills in once complaints span multiple cities and categories."
      />
    );
  }

  const cities = Array.from(new Set(data.map((cell) => cell.city))).sort();
  const subCategories = Array.from(new Set(data.map((cell) => cell.sub_category))).sort();
  const maxCount = Math.max(...data.map((cell) => cell.count));
  const byKey = new Map(data.map((cell) => [`${cell.city}|${cell.sub_category}`, cell.count]));

  function colorFor(count: number): string {
    if (count === 0) return "transparent";
    const ratio = count / maxCount;
    const index = Math.min(CONFIDENCE_SEQUENTIAL.length - 1, Math.floor(ratio * CONFIDENCE_SEQUENTIAL.length));
    return CONFIDENCE_SEQUENTIAL[index];
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>City</TableHead>
          {subCategories.map((sub) => (
            <TableHead key={sub} className="text-center">
              {sub}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {cities.map((city) => (
          <TableRow key={city}>
            <TableCell className="font-medium text-foreground">{city}</TableCell>
            {subCategories.map((sub) => {
              const count = byKey.get(`${city}|${sub}`) ?? 0;
              return (
                <TableCell
                  key={sub}
                  className="text-center"
                  style={{ backgroundColor: colorFor(count), color: count > 0 ? "#ffffff" : undefined }}
                  title={`${city} / ${sub}: ${count}`}
                >
                  {count > 0 ? count : ""}
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
