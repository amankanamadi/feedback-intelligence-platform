from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.sanitization import sanitize_optional_text, sanitize_required_text
from app.database.models import FeedbackSource, FeedbackStatus, Priority

# Submission metadata fields - optional, free-text, no fixed vocabulary
# (unlike `source`, which is a closed channel enum).
_METADATA_TEXT_FIELDS = (
    "submitter_user_id_legacy",
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
    # Free-text provenance id for admin bulk-import of external/historical
    # data (e.g. a legacy CRM id) - distinct from the real `user_id` FK,
    # which is always set server-side from the authenticated caller, never
    # from this field.
    submitter_user_id_legacy: Optional[str] = Field(None, max_length=50)
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
        return sanitize_required_text(v, field_name="raw_text")

    @field_validator(*_METADATA_TEXT_FIELDS, mode="before")
    @classmethod
    def _sanitize_metadata_text(cls, v):
        return sanitize_optional_text(v)


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


class FeedbackUserRead(BaseModel):
    """Shape returned to a USER-role caller viewing their own feedback.

    Deliberately excludes every AI-analysis field (category, subcategory,
    sentiment, confidence, themes, summary) and admin-only fields
    (internal_notes, tags) - the router constructs this model explicitly
    rather than relying on a shared response_model, so those attributes
    are never even read off the ORM object for a USER-role response, let
    alone serialized.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_text: str
    status: str
    acknowledgement: Optional[str] = None
    admin_response: Optional[str] = None
    admin_response_at: Optional[datetime] = None
    attachments: list[AttachmentRead] = []
    source: Optional[str] = None
    product: Optional[str] = None
    module: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("status", "source", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v


class FeedbackAdminRead(FeedbackUserRead):
    """Shape returned to an ADMIN-role caller - everything a user sees,
    plus AI analysis results and admin-only workflow fields."""

    main_category: Optional[str] = None
    sub_category: Optional[str] = None
    sentiment: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[int] = None
    summary: Optional[str] = None
    themes: list[str] = []
    tags: list[str] = []
    internal_notes: Optional[str] = None
    user_id: Optional[int] = None
    submitter_user_id_legacy: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    version: Optional[str] = None
    device: Optional[str] = None
    browser: Optional[str] = None
    platform: Optional[str] = None
    region: Optional[str] = None

    @field_validator("main_category", "sub_category", "sentiment", "priority", mode="before")
    @classmethod
    def _admin_enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v

    @field_validator("themes", "tags", mode="before")
    @classmethod
    def _names(cls, v):
        return [item.name if hasattr(item, "name") else item for item in v]


class FeedbackAdminUpdate(BaseModel):
    status: Optional[FeedbackStatus] = None
    priority: Optional[Priority] = None
    tags: Optional[list[str]] = Field(None, max_length=20)
    internal_notes: Optional[str] = Field(None, max_length=5_000)
    admin_response: Optional[str] = Field(None, max_length=5_000)

    @field_validator("internal_notes", "admin_response", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_optional_text(v)

    @field_validator("tags", mode="before")
    @classmethod
    def _sanitize_tags(cls, v):
        if v is None:
            return v
        return [sanitize_optional_text(tag) for tag in v if sanitize_optional_text(tag)]
