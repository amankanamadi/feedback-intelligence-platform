from __future__ import annotations

import enum
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.database.models import FeedbackSource

# Built from bare codepoints (via chr()) rather than embedding the actual
# invisible/control characters in this source file, which would be both
# unreadable and easy to silently corrupt in an editor.
_DANGEROUS_CODEPOINT_RANGES = [
    (0x200B, 0x200F),  # zero-width space/joiners, LRM/RLM marks (obfuscation)
    (0x202A, 0x202E),  # bidi embedding/override controls (visual spoofing)
    (0x2066, 0x2069),  # bidi isolate controls
    (0xFEFF, 0xFEFF),  # BOM / zero-width no-break space
    (0x00, 0x08),  # C0 controls before tab
    (0x0B, 0x0C),  # vertical tab, form feed
    (0x0E, 0x1F),  # C0 controls after CR, before space
    (0x7F, 0x7F),  # DEL
]
_DANGEROUS_CHARS = re.compile(
    "[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _DANGEROUS_CODEPOINT_RANGES) + "]"
)
# The same character repeated 40+ times in a row - not something legitimate
# feedback does, but a cheap way to waste tokens/cost on every AI call.
_EXCESSIVE_REPETITION = re.compile(r"(.)\1{39,}")

# Submission metadata fields - optional, free-text, no fixed vocabulary
# (unlike `source`, which is a closed channel enum).
_METADATA_TEXT_FIELDS = (
    "user_id",
    "name",
    "email",
    "product",
    "module",
    "version",
    "device",
    "browser",
    "platform",
    "region",
)


class FeedbackCreate(BaseModel):
    raw_text: str = Field(min_length=1, max_length=10_000)
    user_id: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=320)  # RFC 5321 max mailbox length
    source: Optional[FeedbackSource] = None
    product: Optional[str] = Field(None, max_length=100)
    module: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=50)
    device: Optional[str] = Field(None, max_length=100)
    browser: Optional[str] = Field(None, max_length=100)
    platform: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)

    @field_validator("raw_text")
    @classmethod
    def _sanitize_and_validate(cls, v: str) -> str:
        cleaned = _DANGEROUS_CHARS.sub("", v).strip()
        if not cleaned:
            raise ValueError("raw_text must not be empty or whitespace-only")
        if _EXCESSIVE_REPETITION.search(cleaned):
            raise ValueError("raw_text contains excessive repeated characters")
        return cleaned

    @field_validator(*_METADATA_TEXT_FIELDS, mode="before")
    @classmethod
    def _sanitize_metadata_text(cls, v):
        if v is None:
            return v
        cleaned = _DANGEROUS_CHARS.sub("", v).strip()
        return cleaned or None


class BulkFeedbackCreate(BaseModel):
    # Reuses FeedbackCreate's own validators (whitespace/empty rejection,
    # dangerous-character stripping, repetition guard) for every item via
    # Pydantic's nested-model validation - no new validation logic needed.
    # Capped to keep worst-case request latency bounded (each item costs
    # roughly two sequential OpenAI calls).
    items: list[FeedbackCreate] = Field(min_length=1, max_length=25)


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


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
    attachments: list[AttachmentRead] = []
    user_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    product: Optional[str] = None
    module: Optional[str] = None
    version: Optional[str] = None
    device: Optional[str] = None
    browser: Optional[str] = None
    platform: Optional[str] = None
    region: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "main_category", "sub_category", "sentiment", "priority", "source", mode="before"
    )
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v

    @field_validator("themes", mode="before")
    @classmethod
    def _themes_to_names(cls, v):
        return [t.name if hasattr(t, "name") else t for t in v]
