from app.database import crud
from app.database.models import MainCategory, Priority, Sentiment, SubCategory


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
