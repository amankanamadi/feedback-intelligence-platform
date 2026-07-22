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


class AnalyticsSummary(BaseModel):
    total_feedback: int
    classified_feedback: int
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    incidents: int
    service_requests: int
    general_feedback: int
    average_confidence: Optional[float]
    sentiment_breakdown: list[SentimentCount]
    category_breakdown: list[CategoryCount]
    weekly_trend: list[WeeklyTrendPoint]
    confidence_distribution: list[ConfidenceBucket]


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
