import enum
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Table, Column, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small


class MainCategory(str, enum.Enum):
    INCIDENT = "Incident"
    SERVICE_REQUEST = "Service Request"
    GENERAL_FEEDBACK = "General Feedback"


class SubCategory(str, enum.Enum):
    # Incident
    PRODUCT_BUG = "Product Bug"
    APPLICATION_CRASH = "Application Crash"
    LOGIN_ISSUE = "Login Issue"
    PAYMENT_FAILURE = "Payment Failure"
    PERFORMANCE_ISSUE = "Performance Issue"
    SECURITY_ISSUE = "Security Issue"
    DATA_LOSS = "Data Loss"
    INTEGRATION_FAILURE = "Integration Failure"
    # Service Request
    FEATURE_REQUEST = "Feature Request"
    UI_UX_IMPROVEMENT = "UI/UX Improvement"
    DOCUMENTATION_REQUEST = "Documentation Request"
    API_ENHANCEMENT = "API Enhancement"
    ACCESSIBILITY_IMPROVEMENT = "Accessibility Improvement"
    NEW_INTEGRATION = "New Integration"
    # General Feedback
    APPRECIATION = "Appreciation"
    COMPLAINT = "Complaint"
    PRICING_FEEDBACK = "Pricing Feedback"
    CUSTOMER_SUPPORT = "Customer Support"
    QUESTION = "Question"
    SUGGESTION = "Suggestion"


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
    WEB_FORM = "Web Form"
    IN_APP_WIDGET = "In-App Widget"
    MOBILE_APP = "Mobile App"
    EMAIL = "Email"
    API = "API"
    SURVEY = "Survey"
    CHATBOT = "Chatbot"
    QR_CODE = "QR Code"


class FeedbackStatus(str, enum.Enum):
    NEW = "New"
    ACKNOWLEDGED = "Acknowledged"
    IN_REVIEW = "In Review"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


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
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)

    # Auto-generated immediately after classification - the one AI-adjacent
    # field a USER-role response is allowed to include, since it's the
    # submitter's own receipt message, not an analysis internal.
    acknowledgement: Mapped[Optional[str]]

    # Admin workflow fields - never set by AI, only by an admin via
    # PATCH /feedback/{id}.
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus, name="feedback_status_enum"), default=FeedbackStatus.NEW, server_default="NEW"
    )
    internal_notes: Mapped[Optional[str]]  # admin-only, never in a user-facing schema
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
    product: Mapped[Optional[str]]
    module: Mapped[Optional[str]]
    version: Mapped[Optional[str]]
    device: Mapped[Optional[str]]
    browser: Mapped[Optional[str]]
    platform: Mapped[Optional[str]]
    region: Mapped[Optional[str]]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    submitter: Mapped[Optional["User"]] = relationship(back_populates="feedback_items")
    themes: Mapped[list["Theme"]] = relationship(
        secondary=feedback_themes, back_populates="feedback_items"
    )
    tags: Mapped[list["Tag"]] = relationship(secondary=feedback_tags, back_populates="feedback_items")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="feedback", cascade="all, delete-orphan"
    )


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
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    full_name: Mapped[Optional[str]]
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), default=Role.USER, server_default="USER")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedback_items: Mapped[list["Feedback"]] = relationship(back_populates="submitter")


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
