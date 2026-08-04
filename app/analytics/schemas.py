from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class SentimentCount(BaseModel):
    sentiment: str
    count: int


class CategoryCount(BaseModel):
    main_category: str
    count: int


class WeeklyTrendPoint(BaseModel):
    week_start: date
    count: int


class ConfidenceBucket(BaseModel):
    range: str
    count: int


class CityBreakdown(BaseModel):
    city: str
    feedback_count: int
    negative_rate: float


class PropertyHealth(BaseModel):
    property_id: int
    property_name: str
    city: str
    health_score: float
    feedback_count: int
    open_maintenance_count: int
    sla_breached_count: int
    avg_cleanliness_rating: Optional[float] = None


class HostPerformance(BaseModel):
    host_id: int
    host_name: str
    feedback_count: int
    avg_sentiment_score: float
    open_critical_count: int
    sla_breached_count: int
    escalated_count: int
    avg_guest_rating: Optional[float] = None
    performance_score: float


class HeatmapCell(BaseModel):
    city: str
    sub_category: str
    count: int


class WeeklySentimentPoint(BaseModel):
    week_start: date
    positive: int
    neutral: int
    negative: int


class AnalyticsSummary(BaseModel):
    total_feedback: int
    classified_feedback: int
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    guest_reviews: int
    host_complaints: int
    support_tickets: int
    average_confidence: Optional[float]
    sentiment_breakdown: list[SentimentCount]
    category_breakdown: list[CategoryCount]
    weekly_trend: list[WeeklyTrendPoint]
    confidence_distribution: list[ConfidenceBucket]
    guest_satisfaction_score: float
    most_affected_cities: list[CityBreakdown]
    property_health: list[PropertyHealth]
    host_performance: list[HostPerformance]
    avg_resolution_time_hours: Optional[float]
    safety_alerts_open_count: int
    feature_request_trend: list[WeeklyTrendPoint]
    complaint_heatmap: list[HeatmapCell]
    weekly_sentiment_trend: list[WeeklySentimentPoint]


class ThemeFrequency(BaseModel):
    name: str
    count: int


class FeedbackExcerpt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_text: str
    main_category: Optional[str] = None
    sub_category: Optional[str] = None
    sentiment: Optional[str] = None
    priority: Optional[str] = None

    @field_validator("main_category", "sub_category", "sentiment", "priority", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v


class WeeklyReportResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    metrics: AnalyticsSummary
    top_concerns: list[FeedbackExcerpt]
    positive_highlights: list[FeedbackExcerpt]
    executive_summary: str
    key_wins: list[str]
    key_concerns: list[str]
    recommended_actions: list[str]
    emerging_risks: list[str]
    forecast: str
