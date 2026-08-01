export type SentimentCount = { sentiment: string; count: number };
export type CategoryCount = { main_category: string; count: number };
export type WeeklyTrendPoint = { week_start: string; count: number };
export type ConfidenceBucket = { range: string; count: number };
export type CityBreakdown = { city: string; feedback_count: number; negative_rate: number };
export type PropertyHealth = { property_id: number; property_name: string; city: string; health_score: number; feedback_count: number };
export type HostPerformance = { host_name: string; feedback_count: number; avg_sentiment_score: number; open_critical_count: number };

export type AnalyticsSummary = {
  total_feedback: number;
  classified_feedback: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  guest_reviews: number;
  host_complaints: number;
  support_tickets: number;
  average_confidence: number | null;
  sentiment_breakdown: SentimentCount[];
  category_breakdown: CategoryCount[];
  weekly_trend: WeeklyTrendPoint[];
  confidence_distribution: ConfidenceBucket[];
  guest_satisfaction_score: number;
  most_affected_cities: CityBreakdown[];
  property_health: PropertyHealth[];
  host_performance: HostPerformance[];
  avg_resolution_time_hours: number | null;
  safety_alerts_open_count: number;
  feature_request_trend: WeeklyTrendPoint[];
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
