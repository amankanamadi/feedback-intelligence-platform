from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.analytics.schemas import (
    AnalyticsSummary,
    CategoryCount,
    CityBreakdown,
    ConfidenceBucket,
    HeatmapCell,
    HostPerformance,
    PropertyHealth,
    SentimentCount,
    ThemeFrequency,
    WeeklySentimentPoint,
    WeeklyTrendPoint,
)
from app.database import crud
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

# Module-level (not per-call) since they're static SQL expressions with no
# parameters - shared between get_analytics_summary's host_performance
# computation and get_host_performance below, so the two never drift.
_SENTIMENT_SCORE_EXPR = case(
    (Feedback.sentiment == Sentiment.POSITIVE, 1),
    (Feedback.sentiment == Sentiment.NEGATIVE, -1),
    else_=0,
)
_OPEN_CRITICAL_CASE_EXPR = case(
    (and_(Feedback.priority == Priority.CRITICAL, Feedback.status.not_in(_CLOSED_STATUSES)), 1),
    else_=0,
)
_SLA_BREACHED_CASE_EXPR = case((Feedback.sla_breached.is_(True), 1), else_=0)
_ESCALATED_CASE_EXPR = case((Feedback.escalated.is_(True), 1), else_=0)


def _host_performance_score(
    *, avg_sentiment_score: float | None, open_critical: int, sla_breached_count: int,
    escalated_count: int, avg_guest_rating: float | None,
) -> float:
    return round(
        (avg_sentiment_score if avg_sentiment_score is not None else 0.0) * 100
        - 10 * open_critical
        - 5 * sla_breached_count
        - 5 * escalated_count
        + (0.0 if avg_guest_rating is None else (avg_guest_rating - 3) * 20),
        1,
    )


def get_analytics_summary(db: Session, since: datetime | None = None) -> AnalyticsSummary:
    # Every caller of /analytics and /reports/weekly is staff-only
    # (RequireStaff), so there's no scoping concern like the one that
    # limited where this gets called from in the feedback list routes -
    # a single call here keeps sla_breached-derived metrics below from
    # silently undercounting when nobody has hit a listing endpoint
    # recently.
    crud.flag_overdue_sla_breaches(db)

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

    # city x sub_category grid for a chart-based heatmap - bounded to the
    # same top-10 cities as most_affected_cities below (no second city
    # query), sub_category (not main_category) since 3 values is too
    # coarse and includes Guest Review, which isn't a complaint type.
    heatmap_stmt = (
        select(Property.city, Feedback.sub_category, func.count(Feedback.id))
        .join(Property, Feedback.property_id == Property.id)
        .where(Feedback.sub_category.is_not(None))
        .group_by(Property.city, Feedback.sub_category)
    )

    # Sentiment break-out of the existing weekly_trend grouping, for a
    # stacked/multi-line chart - weekly_trend itself stays total-count-only.
    sentiment_week_stmt = (
        select(week_expr, Feedback.sentiment, func.count())
        .where(Feedback.sentiment.is_not(None))
        .group_by(week_expr, Feedback.sentiment)
        .order_by(week_expr)
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
    # Same shape as open_safety_case_expr, for Maintenance-type complaints -
    # a real operational-drag signal, distinct from (and less severe than)
    # an open critical safety case.
    open_maintenance_case_expr = case(
        (
            and_(
                Feedback.sub_category == SubCategory.MAINTENANCE,
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
            func.sum(open_maintenance_case_expr),
            func.sum(_SLA_BREACHED_CASE_EXPR),
            func.avg(Feedback.cleanliness_rating),
        )
        .join(Property, Feedback.property_id == Property.id)
        .group_by(Property.id, Property.name, Property.city)
    )

    host_stmt = (
        select(
            Property.host_id,
            func.max(Property.host_name),
            func.count(Feedback.id),
            func.avg(_SENTIMENT_SCORE_EXPR),
            func.sum(_OPEN_CRITICAL_CASE_EXPR),
            func.sum(_SLA_BREACHED_CASE_EXPR),
            func.sum(_ESCALATED_CASE_EXPR),
            func.avg(Feedback.overall_rating),
        )
        .join(Property, Feedback.property_id == Property.id)
        # Property.host_id is the documented source of truth (see its
        # model docstring) - host_name is only a display cache, so
        # grouping by it instead let two hosts sharing a display name
        # silently merge. func.max(...) aggregates the display text
        # without adding it to GROUP BY (which could fragment one host's
        # rows if that text ever drifted across their properties).
        .where(Property.host_id.is_not(None))
        .group_by(Property.host_id)
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
        heatmap_stmt = heatmap_stmt.where(Feedback.created_at >= since)
        sentiment_week_stmt = sentiment_week_stmt.where(Feedback.created_at >= since)

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
            health_score=round(
                (positive - negative) / count * 100
                - 10 * open_safety
                - 5 * open_maintenance
                - 3 * sla_breached_count
                + (0.0 if avg_cleanliness is None else (float(avg_cleanliness) - 3) * 10),
                1,
            ),
            feedback_count=count,
            open_maintenance_count=open_maintenance or 0,
            sla_breached_count=sla_breached_count or 0,
            avg_cleanliness_rating=round(float(avg_cleanliness), 2) if avg_cleanliness is not None else None,
        )
        for (
            property_id,
            property_name,
            city,
            count,
            positive,
            negative,
            open_safety,
            open_maintenance,
            sla_breached_count,
            avg_cleanliness,
        ) in property_rows
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
            host_id=host_id,
            host_name=host_name,
            feedback_count=count,
            avg_sentiment_score=round(float(avg_score), 2) if avg_score is not None else 0.0,
            open_critical_count=open_critical or 0,
            sla_breached_count=sla_breached_count or 0,
            escalated_count=escalated_count or 0,
            avg_guest_rating=round(float(avg_guest_rating), 2) if avg_guest_rating is not None else None,
            performance_score=_host_performance_score(
                avg_sentiment_score=float(avg_score) if avg_score is not None else None,
                open_critical=open_critical or 0,
                sla_breached_count=sla_breached_count or 0,
                escalated_count=escalated_count or 0,
                avg_guest_rating=float(avg_guest_rating) if avg_guest_rating is not None else None,
            ),
        )
        for (
            host_id,
            host_name,
            count,
            avg_score,
            open_critical,
            sla_breached_count,
            escalated_count,
            avg_guest_rating,
        ) in host_rows
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

    top_cities = {c.city for c in most_affected_cities}
    heatmap_rows = db.execute(heatmap_stmt).all()
    complaint_heatmap = [
        HeatmapCell(city=city, sub_category=sub_category.value, count=count)
        for city, sub_category, count in heatmap_rows
        if city in top_cities
    ]

    sentiment_week_rows = db.execute(sentiment_week_stmt).all()
    sentiment_by_week: dict = {}
    for week_start, sentiment_value, count in sentiment_week_rows:
        sentiment_by_week.setdefault(week_start.date(), {})[sentiment_value] = count
    weekly_sentiment_trend = [
        WeeklySentimentPoint(
            week_start=week,
            positive=counts.get(Sentiment.POSITIVE, 0),
            neutral=counts.get(Sentiment.NEUTRAL, 0),
            negative=counts.get(Sentiment.NEGATIVE, 0),
        )
        for week, counts in sorted(sentiment_by_week.items())
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
        complaint_heatmap=complaint_heatmap,
        weekly_sentiment_trend=weekly_sentiment_trend,
    )


def get_host_performance(db: Session, host_id: int) -> Optional[HostPerformance]:
    """A single host's own Host Performance Score - scoped up front (not
    computed for every host then filtered), for GET /analytics/host-performance.

    The underlying aggregate joins through Feedback, so a host with
    properties but zero feedback ever produces no row - not the same as a
    host with zero properties at all. Falls back to a direct Property
    lookup for the display name in that case, returning a zeroed score
    rather than None (a host who owns a property with no history yet is a
    real, valid state - only "no properties at all" is None).
    """
    crud.flag_overdue_sla_breaches(db)

    stmt = (
        select(
            Property.host_id,
            func.max(Property.host_name),
            func.count(Feedback.id),
            func.avg(_SENTIMENT_SCORE_EXPR),
            func.sum(_OPEN_CRITICAL_CASE_EXPR),
            func.sum(_SLA_BREACHED_CASE_EXPR),
            func.sum(_ESCALATED_CASE_EXPR),
            func.avg(Feedback.overall_rating),
        )
        .join(Property, Feedback.property_id == Property.id)
        .where(Property.host_id == host_id)
        .group_by(Property.host_id)
    )
    row = db.execute(stmt).first()
    if row is not None:
        _, host_name, count, avg_score, open_critical, sla_breached_count, escalated_count, avg_guest_rating = row
        return HostPerformance(
            host_id=host_id,
            host_name=host_name,
            feedback_count=count,
            avg_sentiment_score=round(float(avg_score), 2) if avg_score is not None else 0.0,
            open_critical_count=open_critical or 0,
            sla_breached_count=sla_breached_count or 0,
            escalated_count=escalated_count or 0,
            avg_guest_rating=round(float(avg_guest_rating), 2) if avg_guest_rating is not None else None,
            performance_score=_host_performance_score(
                avg_sentiment_score=float(avg_score) if avg_score is not None else None,
                open_critical=open_critical or 0,
                sla_breached_count=sla_breached_count or 0,
                escalated_count=escalated_count or 0,
                avg_guest_rating=float(avg_guest_rating) if avg_guest_rating is not None else None,
            ),
        )

    host_name = db.scalar(select(func.max(Property.host_name)).where(Property.host_id == host_id))
    if host_name is None:
        return None
    return HostPerformance(
        host_id=host_id,
        host_name=host_name,
        feedback_count=0,
        avg_sentiment_score=0.0,
        open_critical_count=0,
        sla_breached_count=0,
        escalated_count=0,
        avg_guest_rating=None,
        performance_score=0.0,
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
