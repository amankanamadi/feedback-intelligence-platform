from __future__ import annotations

from pydantic import BaseModel, Field

from app.database.models import MainCategory, Priority, Sentiment, SubCategory


class FeedbackClassification(BaseModel):
    main_category: MainCategory
    sub_category: SubCategory
    sentiment: Sentiment
    themes: list[str]
    priority: Priority
    confidence: int = Field(ge=0, le=100)
    summary: str


class WeeklyNarrative(BaseModel):
    executive_summary: str
    key_wins: list[str]
    key_concerns: list[str]
    recommended_actions: list[str]
