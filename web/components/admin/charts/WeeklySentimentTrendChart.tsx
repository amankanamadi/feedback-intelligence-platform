"use client";

import "./chart-setup";
import { Bar } from "react-chartjs-2";
import { CHART_GRID_COLOR, CHART_TEXT_COLOR, SENTIMENT_COLORS } from "@/lib/chart-colors";
import { formatDate } from "@/lib/format";
import type { WeeklySentimentPoint } from "@/types/analytics";

export function WeeklySentimentTrendChart({ data }: { data: WeeklySentimentPoint[] }) {
  return (
    <Bar
      data={{
        labels: data.map((d) => formatDate(d.week_start)),
        datasets: [
          { label: "Positive", data: data.map((d) => d.positive), backgroundColor: SENTIMENT_COLORS.Positive },
          { label: "Neutral", data: data.map((d) => d.neutral), backgroundColor: SENTIMENT_COLORS.Neutral },
          { label: "Negative", data: data.map((d) => d.negative), backgroundColor: SENTIMENT_COLORS.Negative },
        ],
      }}
      options={{
        plugins: { legend: { position: "bottom", labels: { color: CHART_TEXT_COLOR } } },
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: { color: CHART_TEXT_COLOR } },
          y: {
            stacked: true,
            beginAtZero: true,
            ticks: { precision: 0, color: CHART_TEXT_COLOR },
            grid: { color: CHART_GRID_COLOR },
          },
        },
      }}
    />
  );
}
