"use client";

import "./chart-setup";
import { Bar } from "react-chartjs-2";
import { CHART_GRID_COLOR, CHART_TEXT_COLOR, SINGLE_SERIES_COLOR } from "@/lib/chart-colors";
import type { ThemeFrequency } from "@/types/analytics";

export function TopThemesChart({ data }: { data: ThemeFrequency[] }) {
  return (
    <Bar
      data={{
        labels: data.map((d) => d.name),
        datasets: [
          {
            label: "Occurrences",
            data: data.map((d) => d.count),
            backgroundColor: SINGLE_SERIES_COLOR,
            borderRadius: 4,
            maxBarThickness: 24,
          },
        ],
      }}
      options={{
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { display: false }, ticks: { color: CHART_TEXT_COLOR } },
          x: {
            beginAtZero: true,
            ticks: { precision: 0, color: CHART_TEXT_COLOR },
            grid: { color: CHART_GRID_COLOR },
          },
        },
      }}
    />
  );
}
