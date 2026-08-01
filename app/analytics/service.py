from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.analytics.schemas import (
    AnalyticsSummary,
    CategoryCount,
    CityBreakdown,
    ConfidenceBucket,
    HostPerformance,
    PropertyHealth,
    SentimentCount,
    ThemeFrequency,
    WeeklyTrendPoint,
)
from app.database.models import (
    Feedback,
    FeedbackStatus,
    MainCategory,
    Priority,
    Property,
    Sentiment,
    SubCategory,
    Theme,
    feedback_themes,
)

CONFIDENCE_BUCKET_ORDER = ["0-20", "21-40", "41-60", "61-80", "81-100"]

# Statuses that mean a case is no longer "open" - used by the safety-alert
# and property-health penalty computations below.
_CLOSED_STATUSES = (FeedbackStatus.RESOLVED, FeedbackStatus.CLOSED)


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

    # --- Guest Experience additions -----------------------------------------

    guest_review_total_stmt = select(func.count()).select_from(Feedback).where(
        Feedback.main_category == MainCategory.GUEST_REVIEW
    )
    guest_review_positive_stmt = select(func.count()).select_from(Feedback).where(
        Feedback.main_category == MainCategory.GUEST_REVIEW,
        Feedback.sentiment == Sentiment.POSITIVE,
    )

    city_stmt = (
        select(
            Property.city,
            func.count(Feedback.id),
            func.sum(case((Feedback.sentiment == Sentiment.NEGATIVE, 1), else_=0)),
        )
        .join(Property, Feedback.property_id == Property.id)
        .group_by(Property.city)
    )

    open_safety_case_expr = case(
        (
            and_(
                Feedback.priority == Priority.CRITICAL,
                Feedback.sub_category == SubCategory.SAFETY,
                Feedback.status.not_in(_CLOSED_STATUSES),
            ),
            1,
        ),
        else_=0,
    )
    property_stmt = (
        select(
            Property.id,
            Property.name,
            Property.city,
            func.count(Feedback.id),
            func.sum(case((Feedback.sentiment == Sentiment.POSITIVE, 1), else_=0)),
            func.sum(case((Feedback.sentiment == Sentiment.NEGATIVE, 1), else_=0)),
            func.sum(open_safety_case_expr),
        )
        .join(Property, Feedback.property_id == Property.id)
        .group_by(Property.id, Property.name, Property.city)
    )

    sentiment_score_expr = case(
        (Feedback.sentiment == Sentiment.POSITIVE, 1),
        (Feedback.sentiment == Sentiment.NEGATIVE, -1),
        else_=0,
    )
    open_critical_case_expr = case(
        (
            and_(Feedback.priority == Priority.CRITICAL, Feedback.status.not_in(_CLOSED_STATUSES)),
            1,
        ),
        else_=0,
    )
    host_stmt = (
        select(
            Property.host_name,
            func.count(Feedback.id),
            func.avg(sentiment_score_expr),
            func.sum(open_critical_case_expr),
        )
        .join(Property, Feedback.property_id == Property.id)
        .group_by(Property.host_name)
    )

    resolution_stmt = select(
        func.avg(func.extract("epoch", Feedback.admin_response_at - Feedback.created_at))
    ).where(Feedback.admin_response_at.is_not(None))

    safety_open_stmt = select(func.count()).select_from(Feedback).where(
        Feedback.priority == Priority.CRITICAL,
        Feedback.sub_category == SubCategory.SAFETY,
        Feedback.status.not_in(_CLOSED_STATUSES),
    )

    feature_trend_stmt = select(week_expr, func.count()).where(
        Feedback.sub_category == SubCategory.FEATURE_REQUESTS
    )

    if since is not None:
        guest_review_total_stmt = guest_review_total_stmt.where(Feedback.created_at >= since)
        guest_review_positive_stmt = guest_review_positive_stmt.where(Feedback.created_at >= since)
        city_stmt = city_stmt.where(Feedback.created_at >= since)
        property_stmt = property_stmt.where(Feedback.created_at >= since)
        host_stmt = host_stmt.where(Feedback.created_at >= since)
        resolution_stmt = resolution_stmt.where(Feedback.created_at >= since)
        safety_open_stmt = safety_open_stmt.where(Feedback.created_at >= since)
        feature_trend_stmt = feature_trend_stmt.where(Feedback.created_at >= since)

    guest_review_total = db.scalar(guest_review_total_stmt) or 0
    guest_review_positive = db.scalar(guest_review_positive_stmt) or 0
    guest_satisfaction_score = (
        round(guest_review_positive / guest_review_total * 100, 1) if guest_review_total else 0.0
    )

    city_rows = db.execute(city_stmt.order_by(func.count(Feedback.id).desc()).limit(10)).all()
    most_affected_cities = [
        CityBreakdown(
            city=city,
            feedback_count=count,
            negative_rate=round(negative / count * 100, 1) if count else 0.0,
        )
        for city, count, negative in city_rows
    ]

    property_rows = db.execute(property_stmt).all()
    property_health_all = [
        PropertyHealth(
            property_id=property_id,
            property_name=property_name,
            city=city,
            health_score=round((positive - negative) / count * 100 - 10 * open_safety, 1),
            feedback_count=count,
        )
        for property_id, property_name, city, count, positive, negative, open_safety in property_rows
        if count
    ]
    # Bottom 10 (needing attention) plus top 10 (best performing) by health
    # score - on a small dataset these can overlap, which is fine.
    needs_attention = sorted(property_health_all, key=lambda p: p.health_score)[:10]
    best_performing = sorted(property_health_all, key=lambda p: p.health_score, reverse=True)[:10]
    property_health = needs_attention + best_performing

    host_rows = db.execute(host_stmt).all()
    host_performance = [
        HostPerformance(
            host_name=host_name,
            feedback_count=count,
            avg_sentiment_score=round(float(avg_score), 2) if avg_score is not None else 0.0,
            open_critical_count=open_critical or 0,
        )
        for host_name, count, avg_score, open_critical in host_rows
    ]

    avg_resolution_seconds = db.scalar(resolution_stmt)
    avg_resolution_time_hours = (
        round(float(avg_resolution_seconds) / 3600, 1) if avg_resolution_seconds is not None else None
    )

    safety_alerts_open_count = db.scalar(safety_open_stmt) or 0

    feature_trend_rows = db.execute(feature_trend_stmt.group_by(week_expr).order_by(week_expr)).all()
    feature_request_trend = [
        WeeklyTrendPoint(week_start=week_start.date(), count=count) for week_start, count in feature_trend_rows
    ]

    return AnalyticsSummary(
        total_feedback=total_feedback,
        classified_feedback=classified_feedback,
        positive_pct=sentiment_pct(Sentiment.POSITIVE),
        neutral_pct=sentiment_pct(Sentiment.NEUTRAL),
        negative_pct=sentiment_pct(Sentiment.NEGATIVE),
        guest_reviews=category_counts.get(MainCategory.GUEST_REVIEW, 0),
        host_complaints=category_counts.get(MainCategory.HOST_COMPLAINT, 0),
        support_tickets=category_counts.get(MainCategory.SUPPORT_TICKET, 0),
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
        guest_satisfaction_score=guest_satisfaction_score,
        most_affected_cities=most_affected_cities,
        property_health=property_health,
        host_performance=host_performance,
        avg_resolution_time_hours=avg_resolution_time_hours,
        safety_alerts_open_count=safety_alerts_open_count,
        feature_request_trend=feature_request_trend,
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
