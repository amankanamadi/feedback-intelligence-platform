export type SentimentCount = { sentiment: string; count: number };
export type CategoryCount = { main_category: string; count: number };
export type WeeklyTrendPoint = { week_start: string; count: number };
export type ConfidenceBucket = { range: string; count: number };

export type AnalyticsSummary = {
  total_feedback: number;
  classified_feedback: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  incidents: number;
  service_requests: number;
  general_feedback: number;
  average_confidence: number | null;
  sentiment_breakdown: SentimentCount[];
  category_breakdown: CategoryCount[];
  weekly_trend: WeeklyTrendPoint[];
  confidence_distribution: ConfidenceBucket[];
};

export type ThemeFrequency = { name: string; count: number };

export type FeedbackExcerpt = {
  id: number;
  raw_text: string;
  main_category: string | null;
  sub_category: string | null;
  sentiment: string | null;
  priority: string | null;
};

export type WeeklyReportResponse = {
  period_start: string;
  period_end: string;
  metrics: AnalyticsSummary;
  top_concerns: FeedbackExcerpt[];
  positive_highlights: FeedbackExcerpt[];
  executive_summary: string;
  key_wins: string[];
  key_concerns: string[];
  recommended_actions: string[];
};
