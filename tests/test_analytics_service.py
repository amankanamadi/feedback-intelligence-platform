from datetime import datetime, timedelta, timezone

from app.analytics.service import get_analytics_summary, get_host_performance, get_notable_feedback, get_theme_frequencies
from app.core.security import hash_password
from app.database import crud
from app.database.models import (
    FeedbackStatus,
    MainCategory,
    Priority,
    Property,
    PropertyType,
    Role,
    Sentiment,
    SubCategory,
)


def _seed_property(
    db_session, *, name="Sunny Loft", city="Austin", host_name="Jordan Lee", host_id=None
) -> Property:
    property_row = Property(
        name=name, host_name=host_name, city=city, country="USA", property_type=PropertyType.ENTIRE_HOME,
        host_id=host_id,
    )
    db_session.add(property_row)
    db_session.commit()
    return property_row


def _seed_host_user(db_session, *, email) -> int:
    user = crud.create_user(
        db_session, email=email, hashed_password=hash_password("test-password-123"), role=Role.HOST
    )
    return user.id


def _seed_classified(
    db_session,
    raw_text,
    main_category,
    sentiment,
    priority,
    confidence,
    themes,
    *,
    sub_category=SubCategory.CLEANLINESS,
    property_id=None,
    status=FeedbackStatus.NEW,
):
    feedback = crud.create_feedback(db_session, raw_text=raw_text, property_id=property_id)
    feedback = crud.apply_classification(
        db_session,
        feedback,
        main_category=main_category,
        sub_category=sub_category,
        sentiment=sentiment,
        priority=priority,
        confidence=confidence,
        summary="summary",
        theme_names=themes,
        recommended_action="Follow up.",
    )
    feedback.status = status
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_analytics_summary_counts_and_percentages(db_session):
    _seed_classified(
        db_session, "a", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Dirty"]
    )
    _seed_classified(
        db_session, "b", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 80, ["Dirty"]
    )
    _seed_classified(
        db_session,
        "c",
        MainCategory.SUPPORT_TICKET,
        Sentiment.POSITIVE,
        Priority.LOW,
        100,
        ["Appreciation"],
        sub_category=SubCategory.FEATURE_REQUESTS,
    )
    crud.create_feedback(db_session, raw_text="unclassified, still counts toward total")

    summary = get_analytics_summary(db_session)

    assert summary.total_feedback == 4
    assert summary.classified_feedback == 3
    assert summary.guest_reviews == 2
    assert summary.support_tickets == 1
    assert summary.negative_pct == round(2 / 3 * 100, 1)
    assert summary.positive_pct == round(1 / 3 * 100, 1)
    assert summary.average_confidence == round((90 + 80 + 100) / 3, 1)


def test_analytics_summary_empty_database_has_no_divide_by_zero(db_session):
    summary = get_analytics_summary(db_session)

    assert summary.total_feedback == 0
    assert summary.positive_pct == 0.0
    assert summary.average_confidence is None
    assert len(summary.confidence_distribution) == 5
    assert all(bucket.count == 0 for bucket in summary.confidence_distribution)
    assert summary.guest_satisfaction_score == 0.0
    assert summary.most_affected_cities == []
    assert summary.property_health == []
    assert summary.host_performance == []
    assert summary.avg_resolution_time_hours is None
    assert summary.safety_alerts_open_count == 0
    assert summary.feature_request_trend == []
    assert summary.complaint_heatmap == []
    assert summary.weekly_sentiment_trend == []


def test_analytics_summary_since_filter_excludes_older_rows(db_session):
    old = _seed_classified(
        db_session, "old", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )
    old.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.commit()

    _seed_classified(
        db_session, "recent", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )

    since = datetime.now(timezone.utc) - timedelta(days=7)
    summary = get_analytics_summary(db_session, since=since)

    assert summary.total_feedback == 1


def test_confidence_distribution_buckets_correctly(db_session):
    _seed_classified(db_session, "low", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.LOW, 15, [])
    _seed_classified(db_session, "high", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.LOW, 95, [])

    summary = get_analytics_summary(db_session)
    buckets = {b.range: b.count for b in summary.confidence_distribution}

    assert buckets["0-20"] == 1
    assert buckets["81-100"] == 1
    assert buckets["21-40"] == 0


def test_theme_frequencies_orders_by_count_desc(db_session):
    _seed_classified(
        db_session, "a", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Popular"]
    )
    _seed_classified(
        db_session, "b", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Popular"]
    )
    _seed_classified(
        db_session, "c", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Rare"]
    )

    frequencies = get_theme_frequencies(db_session)

    assert frequencies[0].name == "Popular"
    assert frequencies[0].count == 2
    assert frequencies[1].name == "Rare"
    assert frequencies[1].count == 1


def test_analytics_summary_single_entry_gives_clean_100_percent(db_session):
    _seed_classified(
        db_session, "only one", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 77, ["Solo"]
    )

    summary = get_analytics_summary(db_session)

    assert summary.total_feedback == 1
    assert summary.classified_feedback == 1
    assert summary.negative_pct == 100.0
    assert summary.positive_pct == 0.0
    assert summary.neutral_pct == 0.0
    assert summary.guest_reviews == 1
    assert summary.host_complaints == 0
    assert summary.support_tickets == 0
    assert summary.average_confidence == 77.0
    assert len(summary.weekly_trend) == 1
    assert summary.weekly_trend[0].count == 1


def test_analytics_summary_omits_categories_with_no_data(db_session):
    _seed_classified(
        db_session, "a", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )
    _seed_classified(
        db_session, "b", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )

    summary = get_analytics_summary(db_session)

    assert summary.guest_reviews == 2
    assert summary.host_complaints == 0
    assert summary.support_tickets == 0
    # Only categories that actually have data appear in the chart-ready list -
    # no phantom zero-count entries for categories with nothing recorded.
    assert [c.main_category for c in summary.category_breakdown] == ["Guest Review"]


def test_analytics_summary_omits_sentiments_with_no_data(db_session):
    _seed_classified(
        db_session, "a", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )

    summary = get_analytics_summary(db_session)

    assert summary.positive_pct == 0.0
    assert summary.neutral_pct == 0.0
    assert [s.sentiment for s in summary.sentiment_breakdown] == ["Negative"]


def test_analytics_summary_extreme_skew_rounds_sensibly(db_session):
    for i in range(9):
        _seed_classified(
            db_session, f"neg-{i}", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, []
        )
    _seed_classified(
        db_session, "pos", MainCategory.SUPPORT_TICKET, Sentiment.POSITIVE, Priority.LOW, 90, [],
        sub_category=SubCategory.FEATURE_REQUESTS,
    )

    summary = get_analytics_summary(db_session)

    assert summary.total_feedback == 10
    assert summary.negative_pct == 90.0
    assert summary.positive_pct == 10.0
    assert summary.neutral_pct == 0.0


def test_theme_frequencies_empty_when_no_themes_recorded(db_session):
    _seed_classified(
        db_session, "no themes", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )

    frequencies = get_theme_frequencies(db_session)

    assert frequencies == []


def test_duplicate_raw_text_counted_as_separate_feedback_in_analytics(db_session):
    _seed_classified(
        db_session,
        "Duplicate feedback text.",
        MainCategory.GUEST_REVIEW,
        Sentiment.NEGATIVE,
        Priority.HIGH,
        90,
        [],
    )
    _seed_classified(
        db_session,
        "Duplicate feedback text.",
        MainCategory.GUEST_REVIEW,
        Sentiment.NEGATIVE,
        Priority.HIGH,
        90,
        [],
    )

    summary = get_analytics_summary(db_session)

    # Phase 1's policy is to allow duplicate submissions (detect + log, never
    # reject or collapse) - analytics must reflect that, not silently
    # deduplicate identical text.
    assert summary.total_feedback == 2
    assert summary.guest_reviews == 2


def test_get_notable_feedback_filters_by_priority(db_session):
    _seed_classified(
        db_session, "urgent", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.CRITICAL, 90, [],
        sub_category=SubCategory.SAFETY,
    )
    _seed_classified(
        db_session, "routine", MainCategory.SUPPORT_TICKET, Sentiment.NEUTRAL, Priority.LOW, 90, [],
        sub_category=SubCategory.BOOKING_EXPERIENCE,
    )

    since = datetime.now(timezone.utc) - timedelta(days=7)
    notable = get_notable_feedback(db_session, since=since, priority_in=[Priority.CRITICAL])

    assert len(notable) == 1
    assert notable[0].raw_text == "urgent"


def test_get_notable_feedback_filters_by_main_category(db_session):
    # Same sentiment, different main_category - main_category alone must
    # decide who survives the filter, since this is exactly what the
    # weekly report's positive_highlights relies on to avoid surfacing a
    # mistagged-Positive Support Ticket as a "win."
    _seed_classified(
        db_session, "glowing review", MainCategory.GUEST_REVIEW, Sentiment.POSITIVE, Priority.LOW, 90, [],
    )
    _seed_classified(
        db_session, "positive-toned feature request", MainCategory.SUPPORT_TICKET, Sentiment.POSITIVE, Priority.LOW, 90, [],
        sub_category=SubCategory.FEATURE_REQUESTS,
    )

    since = datetime.now(timezone.utc) - timedelta(days=7)
    notable = get_notable_feedback(
        db_session, since=since, sentiment=Sentiment.POSITIVE, main_category=MainCategory.GUEST_REVIEW
    )

    assert len(notable) == 1
    assert notable[0].raw_text == "glowing review"


def test_guest_satisfaction_score_reflects_positive_guest_review_share(db_session):
    _seed_classified(db_session, "great stay", MainCategory.GUEST_REVIEW, Sentiment.POSITIVE, Priority.LOW, 90, [])
    _seed_classified(db_session, "bad stay", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, [])
    # Non guest-review feedback must not dilute the guest satisfaction denominator.
    _seed_classified(
        db_session, "app bug", MainCategory.SUPPORT_TICKET, Sentiment.NEGATIVE, Priority.MEDIUM, 90, [],
        sub_category=SubCategory.APP_ISSUES,
    )

    summary = get_analytics_summary(db_session)

    assert summary.guest_satisfaction_score == 50.0


def test_most_affected_cities_reports_feedback_count_and_negative_rate(db_session):
    property_row = _seed_property(db_session, city="Austin")
    _seed_classified(
        db_session, "a", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, [],
        property_id=property_row.id,
    )
    _seed_classified(
        db_session, "b", MainCategory.GUEST_REVIEW, Sentiment.POSITIVE, Priority.LOW, 90, [],
        property_id=property_row.id,
    )

    summary = get_analytics_summary(db_session)

    assert len(summary.most_affected_cities) == 1
    city_breakdown = summary.most_affected_cities[0]
    assert city_breakdown.city == "Austin"
    assert city_breakdown.feedback_count == 2
    assert city_breakdown.negative_rate == 50.0


def test_property_health_penalizes_open_critical_safety_cases(db_session):
    property_row = _seed_property(db_session)
    _seed_classified(
        db_session,
        "unsafe",
        MainCategory.HOST_COMPLAINT,
        Sentiment.NEGATIVE,
        Priority.CRITICAL,
        90,
        [],
        sub_category=SubCategory.SAFETY,
        property_id=property_row.id,
        status=FeedbackStatus.NEW,
    )

    summary = get_analytics_summary(db_session)

    # With only one property overall, it legitimately lands in both the
    # "needs attention" (bottom 10) and "best performing" (top 10) slices
    # of a single combined list - see get_analytics_summary's comment on
    # small-dataset overlap. Assert on the score, not on a specific count.
    matching = [p for p in summary.property_health if p.property_id == property_row.id]
    assert matching
    assert all(p.health_score < 0 for p in matching)
    assert summary.safety_alerts_open_count == 1


def test_property_health_counts_open_maintenance_complaints(db_session):
    property_row = _seed_property(db_session)
    _seed_classified(
        db_session, "leaky faucet", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.MEDIUM, 90, [],
        sub_category=SubCategory.MAINTENANCE, property_id=property_row.id, status=FeedbackStatus.NEW,
    )

    summary = get_analytics_summary(db_session)

    matching = [p for p in summary.property_health if p.property_id == property_row.id]
    assert matching
    assert matching[0].open_maintenance_count == 1


def test_property_health_counts_sla_breaches_and_averages_cleanliness_rating(db_session):
    property_row = _seed_property(db_session)
    guest_id = crud.create_user(
        db_session, email="analytics-prop-guest@example.com", hashed_password=hash_password("test-password-123")
    ).id
    booking = crud.create_booking(
        db_session, confirmation_code="ANALYTICS-PROP-001", guest_id=guest_id, property_id=property_row.id,
        check_in_date=datetime.now(timezone.utc).date(), check_out_date=datetime.now(timezone.utc).date(),
    )
    feedback = crud.create_feedback(
        db_session, raw_text="Stay review.", property_id=property_row.id, booking_id=booking.id,
        overall_rating=4, cleanliness_rating=2,
    )
    feedback.sla_breached = True
    db_session.commit()

    summary = get_analytics_summary(db_session)

    matching = [p for p in summary.property_health if p.property_id == property_row.id]
    assert matching
    assert matching[0].sla_breached_count == 1
    assert matching[0].avg_cleanliness_rating == 2.0


def test_safety_alerts_open_count_excludes_resolved_cases(db_session):
    property_row = _seed_property(db_session)
    _seed_classified(
        db_session,
        "unsafe but resolved",
        MainCategory.HOST_COMPLAINT,
        Sentiment.NEGATIVE,
        Priority.CRITICAL,
        90,
        [],
        sub_category=SubCategory.SAFETY,
        property_id=property_row.id,
        status=FeedbackStatus.RESOLVED,
    )

    summary = get_analytics_summary(db_session)

    assert summary.safety_alerts_open_count == 0


def test_host_performance_counts_feedback_and_open_critical_cases(db_session):
    host_id = _seed_host_user(db_session, email="jordan@example.com")
    property_row = _seed_property(db_session, host_name="Jordan Lee", host_id=host_id)
    _seed_classified(
        db_session, "critical issue", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.CRITICAL, 90, [],
        sub_category=SubCategory.MAINTENANCE, property_id=property_row.id,
    )

    summary = get_analytics_summary(db_session)

    matching = [h for h in summary.host_performance if h.host_id == host_id]
    assert len(matching) == 1
    assert matching[0].host_name == "Jordan Lee"
    assert matching[0].feedback_count == 1
    assert matching[0].open_critical_count == 1


def test_host_performance_excludes_properties_without_a_linked_host(db_session):
    property_row = _seed_property(db_session, host_name="No Account Host", host_id=None)
    _seed_classified(
        db_session, "some issue", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.MEDIUM, 90, [],
        property_id=property_row.id,
    )

    summary = get_analytics_summary(db_session)

    assert summary.host_performance == []


def test_host_performance_does_not_merge_two_hosts_with_the_same_display_name(db_session):
    host_a_id = _seed_host_user(db_session, email="host-a@example.com")
    host_b_id = _seed_host_user(db_session, email="host-b@example.com")
    property_a = _seed_property(db_session, name="Property A", host_name="Sam Rivera", host_id=host_a_id)
    property_b = _seed_property(db_session, name="Property B", host_name="Sam Rivera", host_id=host_b_id)
    _seed_classified(
        db_session, "a", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.LOW, 90, [],
        property_id=property_a.id,
    )
    _seed_classified(
        db_session, "b1", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.LOW, 90, [],
        property_id=property_b.id,
    )
    _seed_classified(
        db_session, "b2", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.LOW, 90, [],
        property_id=property_b.id,
    )

    summary = get_analytics_summary(db_session)

    by_id = {h.host_id: h for h in summary.host_performance}
    assert len(by_id) == 2
    assert by_id[host_a_id].feedback_count == 1
    assert by_id[host_b_id].feedback_count == 2


def test_host_performance_score_reflects_sla_escalation_and_rating_inputs(db_session):
    host_id = _seed_host_user(db_session, email="scored-host@example.com")
    property_row = _seed_property(db_session, host_id=host_id)
    booking = crud.create_booking(
        db_session, confirmation_code="ANALYTICS-HOST-001", guest_id=host_id, property_id=property_row.id,
        check_in_date=datetime.now(timezone.utc).date(), check_out_date=datetime.now(timezone.utc).date(),
    )
    feedback = crud.create_feedback(
        db_session, raw_text="Great stay.", property_id=property_row.id, booking_id=booking.id, overall_rating=5,
    )
    feedback.sentiment = Sentiment.POSITIVE
    feedback.sla_breached = True
    feedback.escalated = True
    db_session.commit()

    summary = get_analytics_summary(db_session)

    matching = [h for h in summary.host_performance if h.host_id == host_id]
    assert len(matching) == 1
    host = matching[0]
    assert host.sla_breached_count == 1
    assert host.escalated_count == 1
    assert host.avg_guest_rating == 5.0
    # avg_sentiment_score=1.0 (all positive) -> 100; -5 (sla) -5 (escalated)
    # + (5-3)*20=40 rating bonus = 130.0
    assert host.performance_score == 130.0


def test_get_host_performance_matches_get_analytics_summary_formula(db_session):
    # Same fixture as test_host_performance_score_reflects_sla_escalation_and_rating_inputs
    # above - proving get_host_performance reuses the exact same formula,
    # not a reimplementation that could drift from it.
    host_id = _seed_host_user(db_session, email="scored-host-2@example.com")
    property_row = _seed_property(db_session, host_id=host_id)
    booking = crud.create_booking(
        db_session, confirmation_code="ANALYTICS-HOST-002", guest_id=host_id, property_id=property_row.id,
        check_in_date=datetime.now(timezone.utc).date(), check_out_date=datetime.now(timezone.utc).date(),
    )
    feedback = crud.create_feedback(
        db_session, raw_text="Great stay.", property_id=property_row.id, booking_id=booking.id, overall_rating=5,
    )
    feedback.sentiment = Sentiment.POSITIVE
    feedback.sla_breached = True
    feedback.escalated = True
    db_session.commit()

    result = get_host_performance(db_session, host_id)

    assert result is not None
    assert result.sla_breached_count == 1
    assert result.escalated_count == 1
    assert result.avg_guest_rating == 5.0
    assert result.performance_score == 130.0


def test_get_host_performance_none_for_host_with_zero_properties(db_session):
    host_id = _seed_host_user(db_session, email="empty-host@example.com")

    assert get_host_performance(db_session, host_id) is None


def test_get_host_performance_zeroed_for_host_with_property_but_no_feedback(db_session):
    host_id = _seed_host_user(db_session, email="new-host@example.com")
    _seed_property(db_session, host_name="New Host", host_id=host_id)

    result = get_host_performance(db_session, host_id)

    assert result is not None
    assert result.feedback_count == 0
    assert result.host_name == "New Host"
    assert result.performance_score == 0.0
    assert result.avg_guest_rating is None


def test_feature_request_trend_only_counts_feature_request_subcategory(db_session):
    _seed_classified(
        db_session, "feature idea", MainCategory.SUPPORT_TICKET, Sentiment.NEUTRAL, Priority.LOW, 90, [],
        sub_category=SubCategory.FEATURE_REQUESTS,
    )
    _seed_classified(
        db_session, "unrelated", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, [],
        sub_category=SubCategory.CLEANLINESS,
    )

    summary = get_analytics_summary(db_session)

    total_feature_requests = sum(point.count for point in summary.feature_request_trend)
    assert total_feature_requests == 1


def test_complaint_heatmap_breaks_down_by_city_and_subcategory(db_session):
    austin = _seed_property(db_session, name="Austin Loft", city="Austin")
    denver = _seed_property(db_session, name="Denver Cabin", city="Denver")
    _seed_classified(
        db_session, "dirty", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, [],
        sub_category=SubCategory.CLEANLINESS, property_id=austin.id,
    )
    _seed_classified(
        db_session, "broken lock", MainCategory.HOST_COMPLAINT, Sentiment.NEGATIVE, Priority.CRITICAL, 90, [],
        sub_category=SubCategory.SAFETY, property_id=denver.id,
    )

    summary = get_analytics_summary(db_session)

    cells = {(c.city, c.sub_category): c.count for c in summary.complaint_heatmap}
    assert cells[("Austin", "Cleanliness")] == 1
    assert cells[("Denver", "Safety")] == 1


def test_weekly_sentiment_trend_breaks_out_by_sentiment(db_session):
    positive = _seed_classified(
        db_session, "great", MainCategory.GUEST_REVIEW, Sentiment.POSITIVE, Priority.LOW, 90, [],
    )
    negative = _seed_classified(
        db_session, "bad", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, Priority.HIGH, 90, [],
    )
    for row in (positive, negative):
        row.created_at = datetime.now(timezone.utc)
    db_session.commit()

    summary = get_analytics_summary(db_session)

    assert len(summary.weekly_sentiment_trend) == 1
    point = summary.weekly_sentiment_trend[0]
    assert point.positive == 1
    assert point.negative == 1
    assert point.neutral == 0
