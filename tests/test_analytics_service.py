from datetime import datetime, timedelta, timezone

from app.analytics.service import get_analytics_summary, get_notable_feedback, get_theme_frequencies
from app.database import crud
from app.database.models import MainCategory, Priority, Sentiment, SubCategory


def _seed_classified(db_session, raw_text, main_category, sentiment, priority, confidence, themes):
    feedback = crud.create_feedback(db_session, raw_text=raw_text)
    return crud.apply_classification(
        db_session,
        feedback,
        main_category=main_category,
        sub_category=SubCategory.PERFORMANCE_ISSUE,
        sentiment=sentiment,
        priority=priority,
        confidence=confidence,
        summary="summary",
        theme_names=themes,
    )


def test_analytics_summary_counts_and_percentages(db_session):
    _seed_classified(
        db_session, "a", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Perf"]
    )
    _seed_classified(
        db_session, "b", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.HIGH, 80, ["Perf"]
    )
    _seed_classified(
        db_session,
        "c",
        MainCategory.GENERAL_FEEDBACK,
        Sentiment.POSITIVE,
        Priority.LOW,
        100,
        ["Appreciation"],
    )
    crud.create_feedback(db_session, raw_text="unclassified, still counts toward total")

    summary = get_analytics_summary(db_session)

    assert summary.total_feedback == 4
    assert summary.classified_feedback == 3
    assert summary.incidents == 2
    assert summary.general_feedback == 1
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


def test_analytics_summary_since_filter_excludes_older_rows(db_session):
    old = _seed_classified(
        db_session, "old", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )
    old.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.commit()

    _seed_classified(
        db_session, "recent", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.HIGH, 90, []
    )

    since = datetime.now(timezone.utc) - timedelta(days=7)
    summary = get_analytics_summary(db_session, since=since)

    assert summary.total_feedback == 1


def test_confidence_distribution_buckets_correctly(db_session):
    _seed_classified(db_session, "low", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.LOW, 15, [])
    _seed_classified(db_session, "high", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.LOW, 95, [])

    summary = get_analytics_summary(db_session)
    buckets = {b.range: b.count for b in summary.confidence_distribution}

    assert buckets["0-20"] == 1
    assert buckets["81-100"] == 1
    assert buckets["21-40"] == 0


def test_theme_frequencies_orders_by_count_desc(db_session):
    _seed_classified(
        db_session, "a", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Popular"]
    )
    _seed_classified(
        db_session, "b", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Popular"]
    )
    _seed_classified(
        db_session, "c", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.HIGH, 90, ["Rare"]
    )

    frequencies = get_theme_frequencies(db_session)

    assert frequencies[0].name == "Popular"
    assert frequencies[0].count == 2
    assert frequencies[1].name == "Rare"
    assert frequencies[1].count == 1


def test_get_notable_feedback_filters_by_priority(db_session):
    _seed_classified(
        db_session, "urgent", MainCategory.INCIDENT, Sentiment.NEGATIVE, Priority.CRITICAL, 90, []
    )
    _seed_classified(
        db_session, "routine", MainCategory.SERVICE_REQUEST, Sentiment.NEUTRAL, Priority.LOW, 90, []
    )

    since = datetime.now(timezone.utc) - timedelta(days=7)
    notable = get_notable_feedback(db_session, since=since, priority_in=[Priority.CRITICAL])

    assert len(notable) == 1
    assert notable[0].raw_text == "urgent"
