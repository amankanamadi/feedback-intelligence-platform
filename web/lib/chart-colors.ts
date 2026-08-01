// Chart color assignment, following the dataviz skill's method: color by
// the job it does, not by vibe. Values are the skill's pre-validated
// reference palette (references/palette.md) - categorical slots 1-3 are
// documented to pass all-pairs CVD checks in both light/dark modes, so
// reused directly rather than re-deriving and re-validating our own.

// Categorical - main_category has no inherent order or good/bad meaning,
// so it gets fixed-order categorical hues (never reused for status).
export const CATEGORY_COLORS: Record<string, string> = {
  "Guest Review": "#2a78d6", // categorical slot 1 (blue)
  "Host Complaint": "#eb6834", // categorical slot 2 (orange)
  "Support Ticket": "#1baf7a", // categorical slot 3 (aqua)
};
export const CATEGORY_FALLBACK = "#898781";

// Status - sentiment IS good/neutral/bad, so it uses the reserved status
// palette, never a categorical hue.
export const SENTIMENT_COLORS: Record<string, string> = {
  Positive: "#0ca30c", // status: good
  Neutral: "#898781", // neutral gray (muted ink, not a hue)
  Negative: "#d03b3b", // status: critical
};

// Sequential - confidence buckets are ordered magnitude (0-20 ... 81-100),
// one hue light->dark, not five distinct categorical colors.
export const CONFIDENCE_SEQUENTIAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"];

// Single-series marks (weekly trend line, top themes bar) - one color,
// no legend needed per the skill ("a single series needs no legend box").
export const SINGLE_SERIES_COLOR = "#2a78d6";

// Chrome - hairline, recessive, one step off the chart surface.
export const CHART_GRID_COLOR = "#e1e0d9";
export const CHART_TEXT_COLOR = "#898781";
