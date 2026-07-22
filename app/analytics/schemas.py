from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


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
