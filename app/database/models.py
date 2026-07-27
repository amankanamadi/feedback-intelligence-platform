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


# Association table for the many-to-many Feedback <-> Theme relationship.
feedback_themes = Table(
    "feedback_themes",
    Base.metadata,
    Column("feedback_id", ForeignKey("feedback.id", ondelete="CASCADE"), primary_key=True),
    Column("theme_id", ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True),
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

    # Submission metadata - who/where/how the feedback came in. Optional
    # since not every channel can supply every field.
    user_id: Mapped[Optional[str]]
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

    themes: Mapped[list["Theme"]] = relationship(
        secondary=feedback_themes, back_populates="feedback_items"
    )


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)

    feedback_items: Mapped[list["Feedback"]] = relationship(
        secondary=feedback_themes, back_populates="themes"
    )
