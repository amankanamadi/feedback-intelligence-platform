from app.ai.schemas import FeedbackClassification
from app.database.models import MainCategory, Priority, Sentiment, SubCategory


def test_submit_feedback_success(client, mock_ai):
    response = client.post("/feedback", json={"raw_text": "Dashboard is very slow to load."})

    assert response.status_code == 201
    body = response.json()
    assert body["raw_text"] == "Dashboard is very slow to load."
    assert body["main_category"] == "Incident"
    assert body["sub_category"] == "Performance Issue"
    assert body["sentiment"] == "Negative"
    assert body["confidence"] == 95
    assert set(body["themes"]) == {"Slow Dashboard", "Performance"}
    mock_ai["classify"].assert_called_once()
    mock_ai["store"].assert_called_once()


def test_submit_feedback_rejects_empty_text(client, mock_ai):
    response = client.post("/feedback", json={"raw_text": ""})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_degrades_gracefully_on_classification_failure(client, mock_ai):
    mock_ai["classify"].side_effect = RuntimeError("OpenAI is down")

    response = client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] is None
    assert body["themes"] == []


def test_submit_feedback_degrades_gracefully_on_embedding_failure(client, mock_ai):
    mock_ai["get_embedding"].side_effect = RuntimeError("network error")

    response = client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] == "Incident"  # classification still ran
    mock_ai["store"].assert_not_called()  # no embedding available to store


def test_get_feedback_not_found(client, mock_ai):
    response = client.get("/feedback/999999")

    assert response.status_code == 404


def test_get_feedback_by_id_round_trips(client, mock_ai):
    created = client.post("/feedback", json={"raw_text": "Round trip test."}).json()

    response = client.get(f"/feedback/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_list_feedback_filters_by_category_and_search(client, mock_ai):
    mock_ai["classify"].side_effect = [
        FeedbackClassification(
            main_category=MainCategory.INCIDENT,
            sub_category=SubCategory.PERFORMANCE_ISSUE,
            sentiment=Sentiment.NEGATIVE,
            themes=["Slow"],
            priority=Priority.HIGH,
            confidence=90,
            summary="s",
        ),
        FeedbackClassification(
            main_category=MainCategory.SERVICE_REQUEST,
            sub_category=SubCategory.FEATURE_REQUEST,
            sentiment=Sentiment.NEUTRAL,
            themes=["Dark Mode"],
            priority=Priority.LOW,
            confidence=90,
            summary="s",
        ),
    ]

    client.post("/feedback", json={"raw_text": "The dashboard is really slow."})
    client.post("/feedback", json={"raw_text": "Please add dark mode."})

    incident_only = client.get("/feedback", params={"main_category": "Incident"}).json()
    assert len(incident_only) == 1
    assert incident_only[0]["main_category"] == "Incident"

    search_results = client.get("/feedback", params={"search": "dark mode"}).json()
    assert len(search_results) == 1
    assert "dark mode" in search_results[0]["raw_text"].lower()


def test_list_feedback_pagination(client, mock_ai):
    for i in range(5):
        client.post("/feedback", json={"raw_text": f"Feedback number {i}"})

    page = client.get("/feedback", params={"skip": 2, "limit": 2}).json()

    assert len(page) == 2
