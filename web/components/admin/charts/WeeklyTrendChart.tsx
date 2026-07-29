"use client";

import "./chart-setup";
import { Line } from "react-chartjs-2";
import { CHART_GRID_COLOR, CHART_TEXT_COLOR, SINGLE_SERIES_COLOR } from "@/lib/chart-colors";
import { formatDate } from "@/lib/format";
import type { WeeklyTrendPoint } from "@/types/analytics";

export function WeeklyTrendChart({ data }: { data: WeeklyTrendPoint[] }) {
  return (
    <Line
      data={{
        labels: data.map((d) => formatDate(d.week_start)),
        datasets: [
          {
            label: "Feedback per week",
            data: data.map((d) => d.count),
            borderColor: SINGLE_SERIES_COLOR,
            backgroundColor: SINGLE_SERIES_COLOR,
            borderWidth: 2,
            pointRadius: 4,
            tension: 0.3,
          },
        ],
      }}
      options={{
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
