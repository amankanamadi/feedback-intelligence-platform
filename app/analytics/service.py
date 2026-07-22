from __future__ import annotations

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
from app.database.models import Feedback, MainCategory, Sentiment, Theme, feedback_themes

CONFIDENCE_BUCKET_ORDER = ["0-20", "21-40", "41-60", "61-80", "81-100"]


def get_analytics_summary(db: Session) -> AnalyticsSummary:
    total_feedback = db.scalar(select(func.count()).select_from(Feedback)) or 0

    sentiment_rows = db.execute(
        select(Feedback.sentiment, func.count())
        .where(Feedback.sentiment.is_not(None))
        .group_by(Feedback.sentiment)
    ).all()
    sentiment_counts = {row[0]: row[1] for row in sentiment_rows}
    classified_feedback = sum(sentiment_counts.values())

    def sentiment_pct(sentiment: Sentiment) -> float:
        count = sentiment_counts.get(sentiment, 0)
        return round(count / classified_feedback * 100, 1) if classified_feedback else 0.0

    category_rows = db.execute(
        select(Feedback.main_category, func.count())
        .where(Feedback.main_category.is_not(None))
        .group_by(Feedback.main_category)
    ).all()
    category_counts = {row[0]: row[1] for row in category_rows}

    average_confidence = db.scalar(select(func.avg(Feedback.confidence)))

    week_expr = func.date_trunc("week", Feedback.created_at)
    weekly_rows = db.execute(
        select(week_expr, func.count()).group_by(week_expr).order_by(week_expr)
    ).all()

    bucket_expr = case(
        (Feedback.confidence <= 20, "0-20"),
        (Feedback.confidence <= 40, "21-40"),
        (Feedback.confidence <= 60, "41-60"),
        (Feedback.confidence <= 80, "61-80"),
        else_="81-100",
    )
    bucket_rows = db.execute(
        select(bucket_expr, func.count())
        .where(Feedback.confidence.is_not(None))
        .group_by(bucket_expr)
    ).all()
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
