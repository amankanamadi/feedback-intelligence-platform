from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.database import crud
from app.database.models import (
    Feedback,
    FeedbackStatus,
    MainCategory,
    Priority,
    Property,
    PropertyType,
    Role,
    Sentiment,
    SubCategory,
)


def _seed(db_session, raw_text, main_category, sentiment, themes, sub_category=SubCategory.CLEANLINESS):
    feedback = crud.create_feedback(db_session, raw_text=raw_text)
    return crud.apply_classification(
        db_session,
        feedback,
        main_category=main_category,
        sub_category=sub_category,
        sentiment=sentiment,
        priority=Priority.MEDIUM,
        confidence=90,
        summary="summary",
        theme_names=themes,
        recommended_action="Follow up.",
    )


def test_analytics_endpoint_returns_expected_shape_on_empty_db(admin_client):
    response = admin_client.get("/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["total_feedback"] == 0
    assert body["sentiment_breakdown"] == []
    assert len(body["confidence_distribution"]) == 5
    assert body["guest_satisfaction_score"] == 0.0
    assert body["most_affected_cities"] == []
    assert body["property_health"] == []
    assert body["host_performance"] == []
    assert body["avg_resolution_time_hours"] is None
    assert body["safety_alerts_open_count"] == 0
    assert body["feature_request_trend"] == []
    assert body["complaint_heatmap"] == []
    assert body["weekly_sentiment_trend"] == []


def test_analytics_endpoint_reflects_seeded_data(admin_client, db_session):
    _seed(db_session, "a", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, ["Dirty"])
    _seed(
        db_session,
        "b",
        MainCategory.SUPPORT_TICKET,
        Sentiment.POSITIVE,
        ["Nice"],
        sub_category=SubCategory.FEATURE_REQUESTS,
    )

    response = admin_client.get("/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["total_feedback"] == 2
    assert body["guest_reviews"] == 1
    assert body["support_tickets"] == 1


def test_themes_endpoint_orders_by_frequency(admin_client, db_session):
    _seed(db_session, "a", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, ["Popular"])
    _seed(db_session, "b", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, ["Popular"])
    _seed(db_session, "c", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, ["Rare"])

    response = admin_client.get("/themes")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"] == "Popular"
    assert body[0]["count"] == 2


def test_themes_endpoint_respects_limit(admin_client, db_session):
    for i in range(5):
        _seed(db_session, f"item {i}", MainCategory.GUEST_REVIEW, Sentiment.NEGATIVE, [f"Theme{i}"])

    response = admin_client.get("/themes", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_host_performance_forbidden_for_guest(user_client):
    response = user_client.get("/analytics/host-performance")

    assert response.status_code == 403


def test_host_performance_forbidden_for_staff(admin_client):
    response = admin_client.get("/analytics/host-performance")

    assert response.status_code == 403


def test_host_performance_returns_null_for_host_with_no_properties(host_client):
    response = host_client.get("/analytics/host-performance")

    assert response.status_code == 200
    assert response.json() is None


def test_host_performance_returns_zeroed_object_for_host_with_property_but_no_feedback(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = Property(
        name="New Listing", host_name="New Host", host_id=host["id"], city="Miami", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    db_session.add(property_row)
    db_session.commit()

    response = host_client.get("/analytics/host-performance")

    assert response.status_code == 200
    body = response.json()
    assert body["feedback_count"] == 0
    assert body["performance_score"] == 0.0
    assert body["host_name"] == "New Host"
    assert body["host_id"] == host["id"]


def test_host_performance_scoped_to_caller_only(host_client, db_session):
    host = host_client.get("/auth/me").json()
    other_host_id = crud.create_user(
        db_session, email="other-host@example.com", hashed_password=hash_password("test-password-123"),
        role=Role.HOST,
    ).id

    my_property = Property(
        name="Mine", host_name="Me", host_id=host["id"], city="Austin", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    other_property = Property(
        name="Not Mine", host_name="Other Host", host_id=other_host_id, city="Denver", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    db_session.add_all([my_property, other_property])
    db_session.commit()

    crud.create_feedback(db_session, raw_text="feedback about mine", property_id=my_property.id)
    crud.create_feedback(db_session, raw_text="feedback about other 1", property_id=other_property.id)
    crud.create_feedback(db_session, raw_text="feedback about other 2", property_id=other_property.id)

    response = host_client.get("/analytics/host-performance")

    assert response.status_code == 200
    body = response.json()
    assert body["host_id"] == host["id"]
    assert body["feedback_count"] == 1


def test_host_performance_flags_overdue_sla_before_counting(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = Property(
        name="Listing", host_name="Host", host_id=host["id"], city="Austin", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    db_session.add(property_row)
    db_session.commit()

    feedback = Feedback(
        raw_text="Overdue complaint.",
        property_id=property_row.id,
        main_category=MainCategory.HOST_COMPLAINT,
        priority=Priority.HIGH,
        status=FeedbackStatus.NEW,
        sla_due_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(feedback)
    db_session.commit()

    response = host_client.get("/analytics/host-performance")

    assert response.status_code == 200
    assert response.json()["sla_breached_count"] == 1
