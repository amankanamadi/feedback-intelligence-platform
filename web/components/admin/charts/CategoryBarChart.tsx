"use client";

import "./chart-setup";
import { Bar } from "react-chartjs-2";
import { CATEGORY_COLORS, CATEGORY_FALLBACK, CHART_GRID_COLOR, CHART_TEXT_COLOR } from "@/lib/chart-colors";
import type { CategoryCount } from "@/types/analytics";

export function CategoryBarChart({ data }: { data: CategoryCount[] }) {
  return (
    <Bar
      data={{
        labels: data.map((d) => d.main_category),
        datasets: [
          {
            label: "Feedback",
            data: data.map((d) => d.count),
            backgroundColor: data.map((d) => CATEGORY_COLORS[d.main_category] ?? CATEGORY_FALLBACK),
            borderRadius: 4,
            maxBarThickness: 48,
          },
        ],
      }}
      options={{
        // Single metric, identity already carried by the x-axis labels -
        // no legend box for a chart with only one series.
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: CHART_TEXT_COLOR } },
          y: {
            beginAtZero: true,
            ticks: { precision: 0, color: CHART_TEXT_COLOR },
            grid: { color: CHART_GRID_COLOR },
          },
        },
      }}
    />
  );
}
