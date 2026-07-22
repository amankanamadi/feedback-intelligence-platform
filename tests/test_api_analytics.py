from app.database import crud
from app.database.models import MainCategory, Priority, Sentiment, SubCategory


def _seed(db_session, raw_text, main_category, sentiment, themes):
    feedback = crud.create_feedback(db_session, raw_text=raw_text)
    return crud.apply_classification(
        db_session,
        feedback,
        main_category=main_category,
        sub_category=SubCategory.PERFORMANCE_ISSUE,
        sentiment=sentiment,
        priority=Priority.MEDIUM,
        confidence=90,
        summary="summary",
        theme_names=themes,
    )


def test_analytics_endpoint_returns_expected_shape_on_empty_db(client):
    response = client.get("/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["total_feedback"] == 0
    assert body["sentiment_breakdown"] == []
    assert len(body["confidence_distribution"]) == 5


def test_analytics_endpoint_reflects_seeded_data(client, db_session):
    _seed(db_session, "a", MainCategory.INCIDENT, Sentiment.NEGATIVE, ["Perf"])
    _seed(db_session, "b", MainCategory.GENERAL_FEEDBACK, Sentiment.POSITIVE, ["Nice"])

    response = client.get("/analytics")

    assert response.status_code == 200
    body = response.json()
    assert body["total_feedback"] == 2
    assert body["incidents"] == 1
    assert body["general_feedback"] == 1


def test_themes_endpoint_orders_by_frequency(client, db_session):
    _seed(db_session, "a", MainCategory.INCIDENT, Sentiment.NEGATIVE, ["Popular"])
    _seed(db_session, "b", MainCategory.INCIDENT, Sentiment.NEGATIVE, ["Popular"])
    _seed(db_session, "c", MainCategory.INCIDENT, Sentiment.NEGATIVE, ["Rare"])

    response = client.get("/themes")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"] == "Popular"
    assert body[0]["count"] == 2


def test_themes_endpoint_respects_limit(client, db_session):
    for i in range(5):
        _seed(db_session, f"item {i}", MainCategory.INCIDENT, Sentiment.NEGATIVE, [f"Theme{i}"])

    response = client.get("/themes", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2
