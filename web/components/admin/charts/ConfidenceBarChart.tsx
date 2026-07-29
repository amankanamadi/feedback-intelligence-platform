"use client";

import "./chart-setup";
import { Bar } from "react-chartjs-2";
import { CHART_GRID_COLOR, CHART_TEXT_COLOR, CONFIDENCE_SEQUENTIAL } from "@/lib/chart-colors";
import type { ConfidenceBucket } from "@/types/analytics";

export function ConfidenceBarChart({ data }: { data: ConfidenceBucket[] }) {
  return (
    <Bar
      data={{
        labels: data.map((d) => d.range),
        datasets: [
          {
            label: "Feedback",
            // Ordered magnitude (0-20 ... 81-100) - one hue, light->dark,
            // never distinct categorical colors per bucket.
            data: data.map((d) => d.count),
            backgroundColor: data.map((_, i) => CONFIDENCE_SEQUENTIAL[i] ?? CONFIDENCE_SEQUENTIAL.at(-1)),
            borderRadius: 4,
            maxBarThickness: 48,
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
