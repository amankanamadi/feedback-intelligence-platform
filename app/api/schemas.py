from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeedbackCreate(BaseModel):
    raw_text: str = Field(min_length=1, max_length=10_000)


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_text: str
    main_category: Optional[str] = None
    sub_category: Optional[str] = None
    sentiment: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[int] = None
    summary: Optional[str] = None
    themes: list[str] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("main_category", "sub_category", "sentiment", "priority", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v

    @field_validator("themes", mode="before")
    @classmethod
    def _themes_to_names(cls, v):
        return [t.name if hasattr(t, "name") else t for t in v]
