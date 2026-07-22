from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.analytics.schemas import (
    AnalyticsSummary,
    CategoryCount,
    ConfidenceBucket,
    SentimentCount,
    ThemeFrequency,
    WeeklyTrendPoint,
)
from app.database.models import Feedback, MainCategory, Priority, Sentiment, Theme, feedback_themes

CONFIDENCE_BUCKET_ORDER = ["0-20", "21-40", "41-60", "61-80", "81-100"]


def get_analytics_summary(db: Session, since: datetime | None = None) -> AnalyticsSummary:
    total_stmt = select(func.count()).select_from(Feedback)
    sentiment_stmt = select(Feedback.sentiment, func.count()).where(Feedback.sentiment.is_not(None))
    category_stmt = select(Feedback.main_category, func.count()).where(
        Feedback.main_category.is_not(None)
    )
    confidence_stmt = select(func.avg(Feedback.confidence))
    bucket_expr = case(
        (Feedback.confidence <= 20, "0-20"),
        (Feedback.confidence <= 40, "21-40"),
        (Feedback.confidence <= 60, "41-60"),
        (Feedback.confidence <= 80, "61-80"),
        else_="81-100",
    )
    bucket_stmt = select(bucket_expr, func.count()).where(Feedback.confidence.is_not(None))

    if since is not None:
        total_stmt = total_stmt.where(Feedback.created_at >= since)
        sentiment_stmt = sentiment_stmt.where(Feedback.created_at >= since)
        category_stmt = category_stmt.where(Feedback.created_at >= since)
        confidence_stmt = confidence_stmt.where(Feedback.created_at >= since)
        bucket_stmt = bucket_stmt.where(Feedback.created_at >= since)

    total_feedback = db.scalar(total_stmt) or 0

    sentiment_rows = db.execute(sentiment_stmt.group_by(Feedback.sentiment)).all()
    sentiment_counts = {row[0]: row[1] for row in sentiment_rows}
    classified_feedback = sum(sentiment_counts.values())

    def sentiment_pct(sentiment: Sentiment) -> float:
        count = sentiment_counts.get(sentiment, 0)
        return round(count / classified_feedback * 100, 1) if classified_feedback else 0.0

    category_rows = db.execute(category_stmt.group_by(Feedback.main_category)).all()
    category_counts = {row[0]: row[1] for row in category_rows}

    average_confidence = db.scalar(confidence_stmt)

    week_expr = func.date_trunc("week", Feedback.created_at)
    weekly_stmt = select(week_expr, func.count())
    if since is not None:
        weekly_stmt = weekly_stmt.where(Feedback.created_at >= since)
    weekly_rows = db.execute(weekly_stmt.group_by(week_expr).order_by(week_expr)).all()

    bucket_rows = db.execute(bucket_stmt.group_by(bucket_expr)).all()
    bucket_counts = {row[0]: row[1] for row in bucket_rows}

    return AnalyticsSummary(
        total_feedback=total_feedback,
        classified_feedback=classified_feedback,
        positive_pct=sentiment_pct(Sentiment.POSITIVE),
        neutral_pct=sentiment_pct(Sentiment.NEUTRAL),
        negative_pct=sentiment_pct(Sentiment.NEGATIVE),
        incidents=category_counts.get(MainCategory.INCIDENT, 0),
        service_requests=category_counts.get(MainCategory.SERVICE_REQUEST, 0),
        general_feedback=category_counts.get(MainCategory.GENERAL_FEEDBACK, 0),
        average_confidence=round(float(average_confidence), 1) if average_confidence is not None else None,
        sentiment_breakdown=[
            SentimentCount(sentiment=sentiment.value, count=count)
            for sentiment, count in sentiment_counts.items()
        ],
        category_breakdown=[
            CategoryCount(main_category=category.value, count=count)
            for category, count in category_counts.items()
        ],
        weekly_trend=[
            WeeklyTrendPoint(week_start=week_start.date(), count=count)
            for week_start, count in weekly_rows
        ],
        confidence_distribution=[
            ConfidenceBucket(range=bucket, count=bucket_counts.get(bucket, 0))
            for bucket in CONFIDENCE_BUCKET_ORDER
        ],
    )


def get_theme_frequencies(db: Session, limit: int = 20) -> list[ThemeFrequency]:
    stmt = (
        select(Theme.name, func.count(feedback_themes.c.feedback_id))
        .join(feedback_themes, feedback_themes.c.theme_id == Theme.id)
        .group_by(Theme.name)
        .order_by(func.count(feedback_themes.c.feedback_id).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [ThemeFrequency(name=name, count=count) for name, count in rows]


def get_notable_feedback(
    db: Session,
    since: datetime,
    *,
    priority_in: list[Priority] | None = None,
    sentiment: Sentiment | None = None,
    limit: int = 5,
) -> list[Feedback]:
    stmt = select(Feedback).where(Feedback.created_at >= since)
    if priority_in:
        stmt = stmt.where(Feedback.priority.in_(priority_in))
    if sentiment is not None:
        stmt = stmt.where(Feedback.sentiment == sentiment)
    stmt = stmt.order_by(Feedback.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))
