import enum
from datetime import date, datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Table, Column, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small


class MainCategory(str, enum.Enum):
    GUEST_REVIEW = "Guest Review"
    HOST_COMPLAINT = "Host Complaint"
    SUPPORT_TICKET = "Support Ticket"


class SubCategory(str, enum.Enum):
    # Guest Review
    CLEANLINESS = "Cleanliness"
    WIFI = "WiFi"
    CHECK_IN = "Check-in"
    AMENITIES = "Amenities"
    HOST_COMMUNICATION = "Host Communication"
    # Host Complaint
    SAFETY = "Safety"
    MAINTENANCE = "Maintenance"
    # Support Ticket
    BOOKING_EXPERIENCE = "Booking Experience"
    PAYMENTS = "Payments"
    REFUNDS = "Refunds"
    APP_ISSUES = "App Issues"
    FEATURE_REQUESTS = "Feature Requests"


class Sentiment(str, enum.Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


class Priority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class FeedbackSource(str, enum.Enum):
    MOBILE_APP = "Mobile App"
    WEBSITE = "Website"
    POST_STAY_SURVEY = "Post-Stay Survey"
    HOST_DASHBOARD = "Host Dashboard"
    EMAIL = "Email"
    SUPPORT_CHAT = "Support Chat"
    API = "API"
    QR_CODE = "QR Code"


class PropertyType(str, enum.Enum):
    ENTIRE_HOME = "Entire Home"
    PRIVATE_ROOM = "Private Room"
    SHARED_ROOM = "Shared Room"


class FeedbackStatus(str, enum.Enum):
    NEW = "New"
    ACKNOWLEDGED = "Acknowledged"
    IN_REVIEW = "In Review"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class BookingStatus(str, enum.Enum):
    UPCOMING = "Upcoming"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class GuestDecision(str, enum.Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


# Where an AI-classified complaint gets routed. Distinct from `Role`: not
# every team here has a login/dashboard (e.g. Payments/Finance/Engineering
# are routing labels only, at least for now), whereas `Role` is strictly
# "who can log in and what can they do."
class ResponsibleTeam(str, enum.Enum):
    HOST = "Host"
    CUSTOMER_SUPPORT = "Customer Support"
    PAYMENTS = "Payments"
    FINANCE = "Finance"
    TRUST_AND_SAFETY = "Trust & Safety"
    ENGINEERING = "Engineering"
    PRODUCT = "Product"


# Association table for the many-to-many Feedback <-> Theme relationship.
# AI-derived, read-only from the API's perspective - never editable via the
# admin PATCH endpoint. Distinct from Tag/feedback_tags below, which is the
# admin-managed equivalent.
feedback_themes = Table(
    "feedback_themes",
    Base.metadata,
    Column("feedback_id", ForeignKey("feedback.id", ondelete="CASCADE"), primary_key=True),
    Column("theme_id", ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True),
)

# Association table for the many-to-many Feedback <-> Tag relationship.
feedback_tags = Table(
    "feedback_tags",
    Base.metadata,
    Column("feedback_id", ForeignKey("feedback.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_text: Mapped[str]

    main_category: Mapped[Optional[MainCategory]] = mapped_column(
        Enum(MainCategory, name="main_category_enum")
    )
    sub_category: Mapped[Optional[SubCategory]] = mapped_column(
        Enum(SubCategory, name="sub_category_enum")
    )
    sentiment: Mapped[Optional[Sentiment]] = mapped_column(Enum(Sentiment, name="sentiment_enum"))
    priority: Mapped[Optional[Priority]] = mapped_column(Enum(Priority, name="priority_enum"))
    confidence: Mapped[Optional[int]]
    summary: Mapped[Optional[str]]
    # AI-suggested next step for the ops team handling this case, e.g.
    # "Escalate to housekeeping vendor" or "Send WiFi troubleshooting guide".
    recommended_action: Mapped[Optional[str]]
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)

    # Auto-generated immediately after classification - the one AI-adjacent
    # field a submitter-role (Guest/Host) response is allowed to include,
    # since it's the submitter's own receipt message, not an analysis
    # internal.
    acknowledgement: Mapped[Optional[str]]

    # Staff workflow fields - never set by AI, only by staff via
    # PATCH /feedback/{id}.
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus, name="feedback_status_enum"), default=FeedbackStatus.NEW, server_default="NEW"
    )
    internal_notes: Mapped[Optional[str]]  # staff-only, never in a submitter-facing schema
    admin_response: Mapped[Optional[str]]  # shown to the submitter once written
    admin_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Real submitter identity, set server-side from the authenticated caller
    # - never client-supplied. ondelete="SET NULL" (not CASCADE): deleting a
    # user account must not delete their feedback history.
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Free-text submitter metadata - who/where/how the feedback came in.
    # Optional since not every channel can supply every field.
    # `submitter_user_id_legacy` predates real accounts (was a free-text,
    # non-FK "user_id" string); kept only for historical export/audit
    # visibility and admin bulk-import provenance, never joined to `users`.
    submitter_user_id_legacy: Mapped[Optional[str]]
    name: Mapped[Optional[str]]
    email: Mapped[Optional[str]]
    source: Mapped[Optional[FeedbackSource]] = mapped_column(Enum(FeedbackSource, name="feedback_source_enum"))
    # Which listing this case is about, when applicable (not every case -
    # e.g. a general app bug report - is tied to a specific property).
    property_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version: Mapped[Optional[str]]
    device: Mapped[Optional[str]]
    browser: Mapped[Optional[str]]
    platform: Mapped[Optional[str]]

    # Which stay this case is about, when applicable. Guest reviews and
    # booking-scoped complaints have one; a general app bug report or
    # feature request typically doesn't.
    booking_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Guest-submitted stay ratings (1-5, enforced at the Pydantic layer, no
    # DB-level CHECK - matches the existing `confidence` column's
    # app-layer-only validation convention). Only populated for
    # main_category == GUEST_REVIEW. The AI pipeline NEVER writes to these
    # columns - property/host ratings are computed only from guest input.
    overall_rating: Mapped[Optional[int]]
    cleanliness_rating: Mapped[Optional[int]]
    communication_rating: Mapped[Optional[int]]
    checkin_rating: Mapped[Optional[int]]
    location_rating: Mapped[Optional[int]]
    value_rating: Mapped[Optional[int]]

    # Expanded AI analysis, populated for complaint-style submissions
    # (Host Complaint / Support Ticket). `recommended_action` above already
    # covers "recommended resolution" - not duplicated here.
    root_cause: Mapped[Optional[str]]
    business_impact: Mapped[Optional[str]]
    executive_summary: Mapped[Optional[str]]
    preventive_recommendation: Mapped[Optional[str]]
    responsible_team: Mapped[Optional[ResponsibleTeam]] = mapped_column(
        Enum(ResponsibleTeam, name="responsible_team_enum")
    )

    # Guest resolution workflow: a rejected resolution auto-escalates.
    guest_decision: Mapped[Optional[GuestDecision]] = mapped_column(
        Enum(GuestDecision, name="guest_decision_enum")
    )
    escalated: Mapped[bool] = mapped_column(default=False, server_default="false")
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # SLA tracking - `sla_due_at` computed from priority at classification
    # time; `sla_breached` flipped by a periodic/on-read check against it.
    sla_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(default=False, server_default="false")

    # Set when semantic duplicate-complaint detection (tightened RAG
    # similarity search) links this item to an earlier, near-identical one.
    duplicate_of_feedback_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("feedback.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    submitter: Mapped[Optional["User"]] = relationship(back_populates="feedback_items")
    property: Mapped[Optional["Property"]] = relationship(back_populates="feedback_items")
    booking: Mapped[Optional["Booking"]] = relationship(back_populates="feedback_items")
    themes: Mapped[list["Theme"]] = relationship(
        secondary=feedback_themes, back_populates="feedback_items"
    )
    tags: Mapped[list["Tag"]] = relationship(secondary=feedback_tags, back_populates="feedback_items")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="feedback", cascade="all, delete-orphan"
    )


class Property(Base):
    """A listing that guest reviews, host complaints, and support tickets can reference.

    Static reference data - seeded once, no create/update/delete API.
    `host_id` is the source of truth for "who owns this listing" (used to
    scope a host's complaint queue); `host_name` stays as a denormalized
    display cache so existing display code doesn't need a join, but new
    code should treat `host_id` as authoritative. `host_id` is nullable
    for migration safety with pre-existing rows, not because a listing can
    legitimately have no host.
    """

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    host_name: Mapped[str]
    host_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    city: Mapped[str] = mapped_column(index=True)
    country: Mapped[str]
    property_type: Mapped[PropertyType] = mapped_column(Enum(PropertyType, name="property_type_enum"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    host: Mapped[Optional["User"]] = relationship(back_populates="hosted_properties")
    feedback_items: Mapped[list["Feedback"]] = relationship(back_populates="property")


class Booking(Base):
    """A stay linking a guest to a property - the anchor for the review and
    complaint workflows.

    `confirmation_code` is the human-facing "Booking ID" a guest types in
    to submit a review or complaint - a separate short code rather than
    exposing the raw integer primary key, so booking IDs aren't
    sequentially guessable.
    """

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    confirmation_code: Mapped[str] = mapped_column(unique=True, index=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    check_in_date: Mapped[date]
    check_out_date: Mapped[date]
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status_enum"),
        default=BookingStatus.UPCOMING,
        server_default="UPCOMING",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    guest: Mapped["User"] = relationship()
    property: Mapped["Property"] = relationship()
    feedback_items: Mapped[list["Feedback"]] = relationship(back_populates="booking")


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)

    feedback_items: Mapped[list["Feedback"]] = relationship(
        secondary=feedback_themes, back_populates="themes"
    )


class Tag(Base):
    """Admin-managed label, distinct from the AI-derived, read-only Theme.

    Assigned via PATCH /feedback/{id}; never written by the classification
    pipeline.
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)

    feedback_items: Mapped[list["Feedback"]] = relationship(
        secondary=feedback_tags, back_populates="tags"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[int] = mapped_column(ForeignKey("feedback.id", ondelete="CASCADE"))
    filename: Mapped[str]
    content_type: Mapped[str]
    size_bytes: Mapped[int]
    # Server-generated relative path under settings.attachments_dir - never
    # built from the client-supplied filename, to avoid path traversal.
    storage_path: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    feedback: Mapped["Feedback"] = relationship(back_populates="attachments")


class Role(str, enum.Enum):
    # Submitter tier - self-registered, scoped to their own feedback.
    GUEST = "GUEST"
    HOST = "HOST"
    # Staff tier - provisioned by manual promotion, can view all feedback.
    SUPPORT_MANAGER = "SUPPORT_MANAGER"
    OPS_MANAGER = "OPS_MANAGER"
    PRODUCT_MANAGER = "PRODUCT_MANAGER"
    TRUST_SAFETY = "TRUST_SAFETY"
    EXEC = "EXEC"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    full_name: Mapped[Optional[str]]
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), default=Role.GUEST, server_default="GUEST")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedback_items: Mapped[list["Feedback"]] = relationship(back_populates="submitter")
    hosted_properties: Mapped[list["Property"]] = relationship(back_populates="host")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # SHA-256 hash of the raw token - never store the usable credential
    # itself, mirroring why passwords are hashed rather than stored plain.
    token_hash: Mapped[str] = mapped_column(unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="reset_tokens")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str]
    link: Mapped[Optional[str]]
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()


class Wishlist(Base):
    """A guest's saved/wishlisted property."""

    __tablename__ = "wishlists"
    __table_args__ = (UniqueConstraint("guest_id", "property_id", name="uq_wishlist_guest_property"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    guest: Mapped["User"] = relationship()
    property: Mapped["Property"] = relationship()
