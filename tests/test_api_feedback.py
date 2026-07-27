from sqlalchemy.exc import OperationalError

from app.ai.schemas import FeedbackClassification
from app.database.models import MainCategory, Priority, Sentiment, SubCategory
from tests.conftest import DEFAULT_CLASSIFICATION


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


def test_submit_feedback_rejects_whitespace_only_text(client, mock_ai):
    response = client.post("/feedback", json={"raw_text": "   \n\t  "})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_strips_surrounding_whitespace(client, mock_ai):
    response = client.post("/feedback", json={"raw_text": "  Dashboard is slow.  "})

    assert response.status_code == 201
    assert response.json()["raw_text"] == "Dashboard is slow."


def test_submit_feedback_strips_zero_width_characters(client, mock_ai):
    zero_width_space = chr(0x200B)
    raw_text = f"The{zero_width_space}dashboard{zero_width_space}is{zero_width_space}slow."

    response = client.post("/feedback", json={"raw_text": raw_text})

    assert response.status_code == 201
    assert response.json()["raw_text"] == "Thedashboardisslow."


def test_submit_feedback_rejects_text_that_is_only_zero_width_characters(client, mock_ai):
    only_zero_width = chr(0x200B) + chr(0x200C) + chr(0x200D)

    response = client.post("/feedback", json={"raw_text": only_zero_width})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_rejects_excessive_character_repetition(client, mock_ai):
    response = client.post("/feedback", json={"raw_text": "a" * 100})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_allows_normal_repeated_punctuation(client, mock_ai):
    response = client.post("/feedback", json={"raw_text": "This is sooooo slow!!!!"})

    assert response.status_code == 201


def test_submit_feedback_degrades_gracefully_on_classification_failure(client, mock_ai):
    mock_ai["classify"].side_effect = RuntimeError("OpenAI is down")

    response = client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] is None
    assert body["themes"] == []


def test_submit_feedback_handles_duplicate_themes_from_ai(client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.INCIDENT,
        sub_category=SubCategory.PERFORMANCE_ISSUE,
        sentiment=Sentiment.NEGATIVE,
        themes=["Slow Dashboard", "Slow Dashboard", "Performance"],
        priority=Priority.MEDIUM,
        confidence=90,
        summary="Customer reports slow dashboard performance.",
    )

    response = client.post("/feedback", json={"raw_text": "The dashboard is really slow."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] == "Incident"  # classification was saved, not dropped
    assert sorted(body["themes"]) == ["Performance", "Slow Dashboard"]


def test_submit_feedback_degrades_gracefully_on_embedding_failure(client, mock_ai):
    mock_ai["get_embedding"].side_effect = RuntimeError("network error")

    response = client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] == "Incident"  # classification still ran
    mock_ai["store"].assert_not_called()  # no embedding available to store


def test_submit_feedback_returns_503_when_database_unavailable(client, mock_ai, monkeypatch):
    import app.api.feedback as feedback_module

    def _raise_operational_error(*args, **kwargs):
        raise OperationalError("INSERT INTO feedback ...", {}, Exception("connection refused"))

    monkeypatch.setattr(feedback_module.crud, "create_feedback", _raise_operational_error)

    response = client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


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


def test_bulk_upload_processes_all_items_in_order(client, mock_ai):
    response = client.post(
        "/bulk-upload",
        json={"items": [{"raw_text": "First item."}, {"raw_text": "Second item."}, {"raw_text": "Third item."}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert [item["raw_text"] for item in body] == ["First item.", "Second item.", "Third item."]
    assert all(item["main_category"] == "Incident" for item in body)
    assert mock_ai["classify"].call_count == 3
    assert mock_ai["store"].call_count == 3


def test_bulk_upload_rejects_empty_items_list(client, mock_ai):
    response = client.post("/bulk-upload", json={"items": []})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_rejects_batch_exceeding_max_size(client, mock_ai):
    items = [{"raw_text": f"Feedback {i}"} for i in range(26)]

    response = client.post("/bulk-upload", json={"items": items})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_rejects_whole_batch_if_any_item_is_invalid(client, mock_ai):
    response = client.post(
        "/bulk-upload",
        json={"items": [{"raw_text": "A valid entry."}, {"raw_text": "   "}]},
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_continues_past_individual_classification_failures(client, mock_ai):
    mock_ai["classify"].side_effect = [
        DEFAULT_CLASSIFICATION,
        RuntimeError("OpenAI is down"),
        DEFAULT_CLASSIFICATION,
    ]

    response = client.post(
        "/bulk-upload",
        json={"items": [{"raw_text": "First item."}, {"raw_text": "Second item."}, {"raw_text": "Third item."}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 3
    assert body[0]["main_category"] == "Incident"
    assert body[1]["main_category"] is None  # failed item still stored, left unclassified
    assert body[2]["main_category"] == "Incident"


def test_submit_feedback_with_full_metadata_round_trips(client, mock_ai):
    response = client.post(
        "/feedback",
        json={
            "raw_text": "Can't upload invoices after today's update.",
            "user_id": "user-42",
            "name": "Jordan Lee",
            "email": "jordan@example.com",
            "source": "Mobile App",
            "product": "Invoicing",
            "module": "Uploads",
            "version": "3.2.1",
            "device": "iPhone 15",
            "browser": "Safari",
            "platform": "iOS",
            "region": "US-East",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == "user-42"
    assert body["name"] == "Jordan Lee"
    assert body["email"] == "jordan@example.com"
    assert body["source"] == "Mobile App"
    assert body["product"] == "Invoicing"
    assert body["module"] == "Uploads"
    assert body["version"] == "3.2.1"
    assert body["device"] == "iPhone 15"
    assert body["browser"] == "Safari"
    assert body["platform"] == "iOS"
    assert body["region"] == "US-East"


def test_submit_feedback_without_metadata_defaults_to_null(client, mock_ai):
    response = client.post("/feedback", json={"raw_text": "Just the text."})

    assert response.status_code == 201
    body = response.json()
    for field in ["user_id", "name", "email", "source", "product", "module", "version", "device", "browser", "platform", "region"]:
        assert body[field] is None


def test_submit_feedback_rejects_invalid_source_value(client, mock_ai):
    response = client.post(
        "/feedback", json={"raw_text": "Anything at all.", "source": "Carrier Pigeon"}
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_captures_metadata_independently_per_item(client, mock_ai):
    response = client.post(
        "/bulk-upload",
        json={
            "items": [
                {"raw_text": "First item.", "source": "Email", "product": "Invoicing"},
                {"raw_text": "Second item."},
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body[0]["source"] == "Email"
    assert body[0]["product"] == "Invoicing"
    assert body[1]["source"] is None
    assert body[1]["product"] is None


def test_list_feedback_filters_by_source(client, mock_ai):
    client.post("/feedback", json={"raw_text": "Via email.", "source": "Email"})
    client.post("/feedback", json={"raw_text": "Via web form.", "source": "Web Form"})

    response = client.get("/feedback", params={"source": "Email"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["raw_text"] == "Via email."


def test_list_feedback_filters_by_product_partial_match(client, mock_ai):
    client.post("/feedback", json={"raw_text": "Invoicing bug.", "product": "Invoicing"})
    client.post("/feedback", json={"raw_text": "Unrelated.", "product": "Payroll"})

    response = client.get("/feedback", params={"product": "invoic"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["raw_text"] == "Invoicing bug."
