import { CONFIDENCE_SEQUENTIAL } from "@/lib/chart-colors";
import type { HeatmapCell } from "@/types/analytics";

// A real Chart.js heatmap needs a matrix-controller plugin this project
// deliberately doesn't depend on (chart-based/no-new-library was the
// established decision for maps/heatmaps) - a plain HTML grid, shaded
// with the existing sequential palette by relative intensity, gets the
// same "where are the hot spots" read without a new dependency.
export function ComplaintHeatmapGrid({ data }: { data: HeatmapCell[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground">No complaint data yet.</p>;
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
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-muted-foreground">City</th>
            {subCategories.map((sub) => (
              <th key={sub} className="px-2 py-1 text-center text-muted-foreground">
                {sub}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cities.map((city) => (
            <tr key={city}>
              <td className="px-2 py-1 font-medium text-foreground">{city}</td>
              {subCategories.map((sub) => {
                const count = byKey.get(`${city}|${sub}`) ?? 0;
                return (
                  <td
                    key={sub}
                    className="px-2 py-1 text-center"
                    style={{ backgroundColor: colorFor(count), color: count > 0 ? "#ffffff" : undefined }}
                    title={`${city} / ${sub}: ${count}`}
                  >
                    {count > 0 ? count : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
