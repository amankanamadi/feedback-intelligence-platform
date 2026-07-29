"use client";

import "./chart-setup";
import { Pie } from "react-chartjs-2";
import { CHART_TEXT_COLOR, SENTIMENT_COLORS } from "@/lib/chart-colors";
import type { SentimentCount } from "@/types/analytics";

export function SentimentPieChart({ data }: { data: SentimentCount[] }) {
  return (
    <Pie
      data={{
        labels: data.map((d) => d.sentiment),
        datasets: [
          {
            data: data.map((d) => d.count),
            backgroundColor: data.map((d) => SENTIMENT_COLORS[d.sentiment] ?? CHART_TEXT_COLOR),
            borderWidth: 0,
          },
        ],
      }}
      options={{
        // Sentiment is a status (good/neutral/bad), not generic identity -
        // color alone would violate "never status color without a label",
        // so the legend (text labels) is mandatory here, not optional.
        plugins: {
          legend: { position: "bottom", labels: { color: CHART_TEXT_COLOR, boxWidth: 12 } },
        },
      }}
    />
  );
}
