from __future__ import annotations

from typing import Optional

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
    # One-sentence, concrete next step for the ops team handling this case,
    # e.g. "Escalate to housekeeping vendor for next-day deep clean."
    recommended_action: str
    # Populated only for Host Complaint / Support Ticket - null for Guest
    # Review, where there's no operational issue to root-cause or route.
    root_cause: Optional[str] = None
    business_impact: Optional[str] = None
    executive_summary: Optional[str] = None
    preventive_recommendation: Optional[str] = None


class WeeklyNarrative(BaseModel):
    """Structured output for the weekly operational summary shown to
    leadership, synthesized from pre-computed metrics and a sample of
    top-priority concerns and positive highlights for the period."""

    executive_summary: str
    key_wins: list[str]
    key_concerns: list[str]
    recommended_actions: list[str]
