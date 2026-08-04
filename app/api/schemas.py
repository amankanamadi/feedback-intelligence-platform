from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.sanitization import sanitize_optional_text, sanitize_required_text
from app.database.models import FeedbackSource, FeedbackStatus, Priority

# Submission metadata fields - optional, free-text, no fixed vocabulary
# (unlike `source`, which is a closed channel enum).
_METADATA_TEXT_FIELDS = (
    "submitter_user_id_legacy",
    "name",
    "email",
    "version",
    "device",
    "browser",
    "platform",
)

# A "stay review" is any submission carrying rating(s) - all six are
# required together (a partial review isn't meaningful), and always tied
# to the completed booking being reviewed.
_RATING_FIELDS = (
    "overall_rating",
    "cleanliness_rating",
    "communication_rating",
    "checkin_rating",
    "location_rating",
    "value_rating",
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
    # Which listing this feedback is about, when applicable - validated
    # against Property in the router (404 if it doesn't reference a real
    # row), not here, since that requires a DB lookup. Ignored (and
    # overwritten by the booking's own property) when booking_id is set -
    # see the router's _process_feedback_submission.
    property_id: Optional[int] = None
    version: Optional[str] = Field(None, max_length=50)
    device: Optional[str] = Field(None, max_length=100)
    browser: Optional[str] = Field(None, max_length=100)
    platform: Optional[str] = Field(None, max_length=100)

    # Stay review fields - present only for a Mandatory Stay Review
    # submission. `booking_id` is validated against the real Booking (and
    # its ownership + COMPLETED status) in the router, not here.
    booking_id: Optional[int] = None
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    checkin_rating: Optional[int] = Field(None, ge=1, le=5)
    location_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)

    @field_validator("raw_text")
    @classmethod
    def _sanitize_and_validate(cls, v: str) -> str:
        return sanitize_required_text(v, field_name="raw_text")

    @field_validator(*_METADATA_TEXT_FIELDS, mode="before")
    @classmethod
    def _sanitize_metadata_text(cls, v):
        return sanitize_optional_text(v)

    @model_validator(mode="after")
    def _validate_stay_review(self) -> "FeedbackCreate":
        ratings = [getattr(self, field) for field in _RATING_FIELDS]
        any_set = any(r is not None for r in ratings)
        all_set = all(r is not None for r in ratings)
        if any_set and not all_set:
            raise ValueError(
                "A stay review requires all six ratings: "
                + ", ".join(_RATING_FIELDS)
            )
        if any_set and self.booking_id is None:
            raise ValueError("A stay review requires a booking_id.")
        return self


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


class FeedbackSubmitterRead(BaseModel):
    """Shape returned to a GUEST/HOST-role caller viewing their own feedback.

    Deliberately excludes every AI-analysis field (category, subcategory,
    sentiment, confidence, themes, summary, recommended_action) and
    staff-only fields (internal_notes, tags) - the router constructs this
    model explicitly rather than relying on a shared response_model, so
    those attributes are never even read off the ORM object for a
    submitter-role response, let alone serialized.
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
    property_id: Optional[int] = None
    # Lightweight property summary for display - populated by the router
    # from `feedback.property` after model_validate, since it isn't a
    # direct attribute on Feedback.
    property_name: Optional[str] = None
    property_city: Optional[str] = None
    # A submitter always sees their own stay review's ratings - these are
    # exactly what they entered, not an AI-analysis field.
    booking_id: Optional[int] = None
    overall_rating: Optional[int] = None
    cleanliness_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    checkin_rating: Optional[int] = None
    location_rating: Optional[int] = None
    value_rating: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("status", "source", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v


class FeedbackStaffRead(FeedbackSubmitterRead):
    """Shape returned to a STAFF-role caller - everything a submitter sees,
    plus AI analysis results and staff-only workflow fields."""

    main_category: Optional[str] = None
    sub_category: Optional[str] = None
    sentiment: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[int] = None
    summary: Optional[str] = None
    # AI-suggested next step for the ops team - internal, never shown to
    # the submitter, hence absent from FeedbackSubmitterRead.
    recommended_action: Optional[str] = None
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

    # Expanded complaint/ticket AI analysis - populated only when
    # main_category is Host Complaint or Support Ticket (see
    # app/api/feedback.py::_process_feedback_submission), null for a
    # Guest Review.
    root_cause: Optional[str] = None
    business_impact: Optional[str] = None
    executive_summary: Optional[str] = None
    preventive_recommendation: Optional[str] = None
    responsible_team: Optional[str] = None
    sla_due_at: Optional[datetime] = None
    sla_breached: bool = False
    # Set when semantic duplicate-complaint detection links this item to
    # an earlier, near-identical one on the same property.
    duplicate_of_feedback_id: Optional[int] = None

    @field_validator(
        "main_category", "sub_category", "sentiment", "priority", "responsible_team", mode="before"
    )
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


class PropertyRead(BaseModel):
    """Static reference data - read-only, no create/update/delete API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    host_name: str
    city: str
    country: str
    property_type: str
    # Computed from guest-submitted stay reviews only - AI never writes a
    # rating, so this is never influenced by classification. Not a direct
    # Feedback/Property attribute, so the router fills it in after
    # model_validate (same pattern as FeedbackSubmitterRead.property_name).
    average_rating: Optional[float] = None

    @field_validator("property_type", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v


class BookingRead(BaseModel):
    """A guest's own booking - the anchor for the review/complaint
    workflows. Only reachable by the booking's own guest or staff (see
    GET /bookings/{confirmation_code})."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    confirmation_code: str
    check_in_date: date
    check_out_date: date
    status: str
    property: PropertyRead

    @field_validator("status", mode="before")
    @classmethod
    def _enum_to_value(cls, v):
        return v.value if isinstance(v, enum.Enum) else v
