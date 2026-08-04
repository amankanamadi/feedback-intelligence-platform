from sqlalchemy.exc import OperationalError

from app.ai.schemas import FeedbackClassification
from app.database.models import MainCategory, Priority, Sentiment, SubCategory
from tests.conftest import DEFAULT_CLASSIFICATION


def test_submit_feedback_success(admin_client, mock_ai):
    response = admin_client.post("/feedback", json={"raw_text": "The apartment was filthy when we arrived."})

    assert response.status_code == 201
    body = response.json()
    assert body["raw_text"] == "The apartment was filthy when we arrived."
    assert body["main_category"] == "Guest Review"
    assert body["sub_category"] == "Cleanliness"
    assert body["sentiment"] == "Negative"
    assert body["confidence"] == 95
    assert set(body["themes"]) == {"Dirty Apartment", "Cleaning Quality"}
    mock_ai["classify"].assert_called_once()
    mock_ai["store"].assert_called_once()


def test_submit_feedback_rejects_empty_text(admin_client, mock_ai):
    response = admin_client.post("/feedback", json={"raw_text": ""})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_rejects_whitespace_only_text(admin_client, mock_ai):
    response = admin_client.post("/feedback", json={"raw_text": "   \n\t  "})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_strips_surrounding_whitespace(admin_client, mock_ai):
    response = admin_client.post("/feedback", json={"raw_text": "  The WiFi is slow.  "})

    assert response.status_code == 201
    assert response.json()["raw_text"] == "The WiFi is slow."


def test_submit_feedback_strips_zero_width_characters(admin_client, mock_ai):
    zero_width_space = chr(0x200B)
    raw_text = f"The{zero_width_space}WiFi{zero_width_space}is{zero_width_space}slow."

    response = admin_client.post("/feedback", json={"raw_text": raw_text})

    assert response.status_code == 201
    assert response.json()["raw_text"] == "TheWiFiisslow."


def test_submit_feedback_rejects_text_that_is_only_zero_width_characters(admin_client, mock_ai):
    only_zero_width = chr(0x200B) + chr(0x200C) + chr(0x200D)

    response = admin_client.post("/feedback", json={"raw_text": only_zero_width})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_rejects_excessive_character_repetition(admin_client, mock_ai):
    response = admin_client.post("/feedback", json={"raw_text": "a" * 100})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_allows_normal_repeated_punctuation(admin_client, mock_ai):
    response = admin_client.post("/feedback", json={"raw_text": "This WiFi is sooooo slow!!!!"})

    assert response.status_code == 201


def test_submit_feedback_degrades_gracefully_on_classification_failure(admin_client, mock_ai):
    mock_ai["classify"].side_effect = RuntimeError("OpenAI is down")

    response = admin_client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] is None
    assert body["themes"] == []


def test_submit_feedback_handles_duplicate_themes_from_ai(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.GUEST_REVIEW,
        sub_category=SubCategory.CLEANLINESS,
        sentiment=Sentiment.NEGATIVE,
        themes=["Dirty Apartment", "Dirty Apartment", "Cleaning Quality"],
        priority=Priority.MEDIUM,
        confidence=90,
        summary="Guest reports the apartment was not clean on arrival.",
        recommended_action="Escalate to housekeeping.",
    )

    response = admin_client.post("/feedback", json={"raw_text": "The apartment was really dirty."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] == "Guest Review"  # classification was saved, not dropped
    assert sorted(body["themes"]) == ["Cleaning Quality", "Dirty Apartment"]


def test_submit_feedback_reconciles_contradictory_classification(admin_client, mock_ai):
    # The model claims Guest Review but Maintenance only ever belongs to
    # Host Complaint - the stored main_category should be corrected, and
    # since that flips it out of Guest Review, routing/SLA should now run
    # too (this exact contradiction previously caused a real maintenance
    # complaint to never reach the host's queue).
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.GUEST_REVIEW,
        sub_category=SubCategory.MAINTENANCE,
        sentiment=Sentiment.NEGATIVE,
        themes=["Pool Cleanliness"],
        priority=Priority.MEDIUM,
        confidence=90,
        summary="Guest reports the pool is dirty.",
        recommended_action="Escalate to housekeeping to clean the pool.",
    )

    response = admin_client.post("/feedback", json={"raw_text": "The swimming pool is dirty."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] == "Host Complaint"
    assert body["sub_category"] == "Maintenance"
    assert body["responsible_team"] == "Host"
    assert body["sla_due_at"] is not None


def test_submit_feedback_degrades_gracefully_on_embedding_failure(admin_client, mock_ai):
    mock_ai["get_embedding"].side_effect = RuntimeError("network error")

    response = admin_client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 201
    body = response.json()
    assert body["main_category"] == "Guest Review"  # classification still ran
    mock_ai["store"].assert_not_called()  # no embedding available to store


def test_submit_feedback_returns_503_when_database_unavailable(admin_client, mock_ai, monkeypatch):
    import app.api.feedback as feedback_module

    def _raise_operational_error(*args, **kwargs):
        raise OperationalError("INSERT INTO feedback ...", {}, Exception("connection refused"))

    monkeypatch.setattr(feedback_module.crud, "create_feedback", _raise_operational_error)

    response = admin_client.post("/feedback", json={"raw_text": "Anything at all."})

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


def test_get_feedback_not_found(admin_client, mock_ai):
    response = admin_client.get("/feedback/999999")

    assert response.status_code == 404


def test_get_feedback_by_id_round_trips(admin_client, mock_ai):
    created = admin_client.post("/feedback", json={"raw_text": "Round trip test."}).json()

    response = admin_client.get(f"/feedback/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_list_feedback_filters_by_category_and_search(admin_client, mock_ai):
    mock_ai["classify"].side_effect = [
        FeedbackClassification(
            main_category=MainCategory.GUEST_REVIEW,
            sub_category=SubCategory.CLEANLINESS,
            sentiment=Sentiment.NEGATIVE,
            themes=["Dirty"],
            priority=Priority.HIGH,
            confidence=90,
            summary="s",
            recommended_action="Escalate to housekeeping.",
        ),
        FeedbackClassification(
            main_category=MainCategory.SUPPORT_TICKET,
            sub_category=SubCategory.FEATURE_REQUESTS,
            sentiment=Sentiment.NEUTRAL,
            themes=["Search Filters"],
            priority=Priority.LOW,
            confidence=90,
            summary="s",
            recommended_action="Log with product team.",
        ),
    ]

    admin_client.post("/feedback", json={"raw_text": "The apartment was really dirty."})
    admin_client.post("/feedback", json={"raw_text": "Please add a pet-friendly search filter."})

    guest_review_only = admin_client.get("/feedback", params={"main_category": "Guest Review"}).json()
    assert len(guest_review_only) == 1
    assert guest_review_only[0]["main_category"] == "Guest Review"

    search_results = admin_client.get("/feedback", params={"search": "pet-friendly"}).json()
    assert len(search_results) == 1
    assert "pet-friendly" in search_results[0]["raw_text"].lower()


def test_list_feedback_pagination(admin_client, mock_ai):
    for i in range(5):
        admin_client.post("/feedback", json={"raw_text": f"Feedback number {i}"})

    page = admin_client.get("/feedback", params={"skip": 2, "limit": 2}).json()

    assert len(page) == 2


def test_bulk_upload_processes_all_items_in_order(admin_client, mock_ai):
    response = admin_client.post(
        "/bulk-upload",
        json={"items": [{"raw_text": "First item."}, {"raw_text": "Second item."}, {"raw_text": "Third item."}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert [item["raw_text"] for item in body] == ["First item.", "Second item.", "Third item."]
    assert all(item["main_category"] == "Guest Review" for item in body)
    assert mock_ai["classify"].call_count == 3
    assert mock_ai["store"].call_count == 3


def test_bulk_upload_rejects_empty_items_list(admin_client, mock_ai):
    response = admin_client.post("/bulk-upload", json={"items": []})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_rejects_batch_exceeding_max_size(admin_client, mock_ai):
    items = [{"raw_text": f"Feedback {i}"} for i in range(26)]

    response = admin_client.post("/bulk-upload", json={"items": items})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_rejects_whole_batch_if_any_item_is_invalid(admin_client, mock_ai):
    response = admin_client.post(
        "/bulk-upload",
        json={"items": [{"raw_text": "A valid entry."}, {"raw_text": "   "}]},
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_continues_past_individual_classification_failures(admin_client, mock_ai):
    mock_ai["classify"].side_effect = [
        DEFAULT_CLASSIFICATION,
        RuntimeError("OpenAI is down"),
        DEFAULT_CLASSIFICATION,
    ]

    response = admin_client.post(
        "/bulk-upload",
        json={"items": [{"raw_text": "First item."}, {"raw_text": "Second item."}, {"raw_text": "Third item."}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 3
    assert body[0]["main_category"] == "Guest Review"
    assert body[1]["main_category"] is None  # failed item still stored, left unclassified
    assert body[2]["main_category"] == "Guest Review"


def test_submit_feedback_with_full_metadata_round_trips(admin_client, db_session, mock_ai):
    from app.database.models import Property, PropertyType

    property_row = Property(
        name="Sunny Loft",
        host_name="Jordan Lee",
        city="Austin",
        country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    db_session.add(property_row)
    db_session.commit()

    response = admin_client.post(
        "/feedback",
        json={
            "raw_text": "Can't check in - the door code isn't working.",
            "submitter_user_id_legacy": "user-42",
            "name": "Jordan Lee",
            "email": "jordan@example.com",
            "source": "Mobile App",
            "property_id": property_row.id,
            "version": "3.2.1",
            "device": "iPhone 15",
            "browser": "Safari",
            "platform": "iOS",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["submitter_user_id_legacy"] == "user-42"
    assert body["name"] == "Jordan Lee"
    assert body["email"] == "jordan@example.com"
    assert body["source"] == "Mobile App"
    assert body["property_id"] == property_row.id
    assert body["property_name"] == "Sunny Loft"
    assert body["property_city"] == "Austin"
    assert body["version"] == "3.2.1"
    assert body["device"] == "iPhone 15"
    assert body["browser"] == "Safari"
    assert body["platform"] == "iOS"


def test_submit_feedback_without_metadata_defaults_to_null(admin_client, mock_ai):
    response = admin_client.post("/feedback", json={"raw_text": "Just the text."})

    assert response.status_code == 201
    body = response.json()
    for field in [
        "submitter_user_id_legacy",
        "name",
        "email",
        "source",
        "property_id",
        "property_name",
        "property_city",
        "version",
        "device",
        "browser",
        "platform",
    ]:
        assert body[field] is None


def test_submit_feedback_rejects_invalid_source_value(admin_client, mock_ai):
    response = admin_client.post(
        "/feedback", json={"raw_text": "Anything at all.", "source": "Carrier Pigeon"}
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_submit_feedback_rejects_unknown_property_id(admin_client, mock_ai):
    response = admin_client.post(
        "/feedback", json={"raw_text": "Anything at all.", "property_id": 999999}
    )

    assert response.status_code == 404
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_captures_metadata_independently_per_item(admin_client, db_session, mock_ai):
    from app.database.models import Property, PropertyType

    property_row = Property(
        name="Sunny Loft",
        host_name="Jordan Lee",
        city="Austin",
        country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    db_session.add(property_row)
    db_session.commit()

    response = admin_client.post(
        "/bulk-upload",
        json={
            "items": [
                {"raw_text": "First item.", "source": "Email", "property_id": property_row.id},
                {"raw_text": "Second item."},
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body[0]["source"] == "Email"
    assert body[0]["property_id"] == property_row.id
    assert body[1]["source"] is None
    assert body[1]["property_id"] is None


def test_list_feedback_filters_by_source(admin_client, mock_ai):
    admin_client.post("/feedback", json={"raw_text": "Via email.", "source": "Email"})
    admin_client.post("/feedback", json={"raw_text": "Via the website.", "source": "Website"})

    response = admin_client.get("/feedback", params={"source": "Email"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["raw_text"] == "Via email."


def test_list_feedback_filters_by_property_id(admin_client, db_session, mock_ai):
    from app.database.models import Property, PropertyType

    property_a = Property(
        name="Sunny Loft", host_name="Jordan Lee", city="Austin", country="USA", property_type=PropertyType.ENTIRE_HOME
    )
    property_b = Property(
        name="Cozy Studio", host_name="Alex Rivera", city="Denver", country="USA", property_type=PropertyType.PRIVATE_ROOM
    )
    db_session.add_all([property_a, property_b])
    db_session.commit()

    admin_client.post("/feedback", json={"raw_text": "Feedback for Sunny Loft.", "property_id": property_a.id})
    admin_client.post("/feedback", json={"raw_text": "Feedback for Cozy Studio.", "property_id": property_b.id})

    response = admin_client.get("/feedback", params={"property_id": property_a.id})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["raw_text"] == "Feedback for Sunny Loft."


def test_bulk_upload_file_accepts_csv(admin_client, mock_ai):
    csv_content = b"raw_text,source\nFirst item.,Website\nSecond item.,Email\n"

    response = admin_client.post(
        "/bulk-upload/file",
        files={"file": ("feedback.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert [item["raw_text"] for item in body] == ["First item.", "Second item."]
    assert body[1]["source"] == "Email"
    assert mock_ai["classify"].call_count == 2


def test_bulk_upload_file_accepts_json(admin_client, mock_ai):
    json_content = b'[{"raw_text": "First item."}, {"raw_text": "Second item."}]'

    response = admin_client.post(
        "/bulk-upload/file",
        files={"file": ("feedback.json", json_content, "application/json")},
    )

    assert response.status_code == 201
    body = response.json()
    assert [item["raw_text"] for item in body] == ["First item.", "Second item."]


def test_bulk_upload_file_rejects_batch_exceeding_cap(admin_client, mock_ai):
    rows = "\n".join(f"Feedback {i}" for i in range(26))
    csv_content = f"raw_text\n{rows}\n".encode()

    response = admin_client.post(
        "/bulk-upload/file",
        files={"file": ("feedback.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_file_rejects_unsupported_extension(admin_client, mock_ai):
    response = admin_client.post(
        "/bulk-upload/file",
        files={"file": ("feedback.txt", b"raw_text\nsomething\n", "text/plain")},
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_bulk_upload_file_rejects_oversized_file(admin_client, mock_ai, monkeypatch):
    import app.api.feedback as feedback_module

    monkeypatch.setattr(feedback_module.get_settings(), "bulk_upload_max_file_bytes", 10)

    response = admin_client.post(
        "/bulk-upload/file",
        files={"file": ("feedback.csv", b"raw_text\nsomething much longer than 10 bytes\n", "text/csv")},
    )

    assert response.status_code == 413
    mock_ai["classify"].assert_not_called()
