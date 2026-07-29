from app.ai.schemas import FeedbackClassification
from app.database.models import MainCategory, Priority, Sentiment, SubCategory

USER_FACING_FIELDS = {
    "id",
    "raw_text",
    "status",
    "acknowledgement",
    "admin_response",
    "admin_response_at",
    "attachments",
    "source",
    "product",
    "module",
    "created_at",
    "updated_at",
}

AI_ONLY_FIELDS = {
    "main_category",
    "sub_category",
    "sentiment",
    "priority",
    "confidence",
    "summary",
    "themes",
    "tags",
    "internal_notes",
    "user_id",
    "submitter_user_id_legacy",
    "name",
    "email",
}


def test_user_response_never_includes_ai_fields(user_client, mock_ai):
    response = user_client.post("/feedback", json={"raw_text": "Dashboard is very slow to load."})

    assert response.status_code == 201
    body = response.json()
    assert AI_ONLY_FIELDS.isdisjoint(body.keys())
    assert set(body.keys()) == USER_FACING_FIELDS


def test_user_list_response_never_includes_ai_fields(user_client, mock_ai):
    user_client.post("/feedback", json={"raw_text": "Dashboard is very slow to load."})

    response = user_client.get("/feedback")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert AI_ONLY_FIELDS.isdisjoint(body[0].keys())


def test_user_can_only_see_own_feedback(client, mock_ai):
    client.post("/auth/register", json={"email": "owner@example.com", "password": "test-password-123"})
    owned_id = client.post("/feedback", json={"raw_text": "My own feedback."}).json()["id"]
    client.post("/auth/logout")

    # Registering again on the same TestClient overwrites its cookies,
    # switching the active session to this second, distinct identity.
    other = client.post("/auth/register", json={"email": "other-user@example.com", "password": "test-password-123"})
    assert other.status_code == 201

    response = client.get(f"/feedback/{owned_id}")
    assert response.status_code == 403

    listed = client.get("/feedback").json()
    assert listed == []


def test_admin_can_see_any_users_feedback(client, admin_client, mock_ai):
    client.post("/auth/register", json={"email": "owner@example.com", "password": "test-password-123"})
    feedback_id = client.post("/feedback", json={"raw_text": "Some feedback."}).json()["id"]

    response = admin_client.get(f"/feedback/{feedback_id}")

    assert response.status_code == 200
    assert response.json()["id"] == feedback_id


def test_bulk_uploaded_feedback_is_invisible_to_users(admin_client, user_client, mock_ai):
    admin_client.post("/bulk-upload", json={"items": [{"raw_text": "Imported historical feedback."}]})

    response = user_client.get("/feedback")

    assert response.status_code == 200
    assert response.json() == []


def test_non_admin_forbidden_from_admin_only_routes(user_client, mock_ai):
    assert user_client.get("/analytics").status_code == 403
    assert user_client.get("/themes").status_code == 403
    assert user_client.get("/reports/weekly").status_code == 403
    assert user_client.get("/feedback/export/csv").status_code == 403
    assert user_client.get("/feedback/export/pdf").status_code == 403
    assert user_client.post("/bulk-upload", json={"items": [{"raw_text": "x"}]}).status_code == 403


def test_unauthenticated_requests_are_rejected(client, mock_ai):
    assert client.post("/feedback", json={"raw_text": "x"}).status_code == 401
    assert client.get("/feedback").status_code == 401
    assert client.get("/feedback/1").status_code == 401
    assert client.get("/analytics").status_code == 401


def test_admin_updates_status_and_response_visible_to_submitter(client, admin_client, mock_ai):
    client.post("/auth/register", json={"email": "submitter@example.com", "password": "test-password-123"})
    feedback_id = client.post("/feedback", json={"raw_text": "The export button is broken."}).json()["id"]

    patch_response = admin_client.patch(
        f"/feedback/{feedback_id}",
        json={"status": "Resolved", "admin_response": "Fixed in the latest release, thanks for flagging this!"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "Resolved"

    submitter_view = client.get(f"/feedback/{feedback_id}").json()
    assert submitter_view["status"] == "Resolved"
    assert submitter_view["admin_response"] == "Fixed in the latest release, thanks for flagging this!"
    assert submitter_view["admin_response_at"] is not None


def test_admin_update_assigns_tags_and_internal_notes(admin_client, mock_ai):
    feedback_id = admin_client.post("/feedback", json={"raw_text": "Please add SSO support."}).json()["id"]

    response = admin_client.patch(
        f"/feedback/{feedback_id}",
        json={"tags": ["enterprise", "sso"], "internal_notes": "Flagged for the Q3 roadmap review."},
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["tags"]) == ["enterprise", "sso"]
    assert body["internal_notes"] == "Flagged for the Q3 roadmap review."


def test_non_admin_cannot_patch_feedback(user_client, mock_ai):
    feedback_id = user_client.post("/feedback", json={"raw_text": "Something."}).json()["id"]

    response = user_client.patch(f"/feedback/{feedback_id}", json={"status": "Resolved"})

    assert response.status_code == 403


def test_acknowledgement_uses_feature_request_template(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.SERVICE_REQUEST,
        sub_category=SubCategory.FEATURE_REQUEST,
        sentiment=Sentiment.NEUTRAL,
        themes=[],
        priority=Priority.LOW,
        confidence=90,
        summary="s",
    )

    body = admin_client.post("/feedback", json={"raw_text": "Please add dark mode."}).json()

    assert "feature request" in body["acknowledgement"].lower()


def test_acknowledgement_uses_appreciation_template(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.GENERAL_FEEDBACK,
        sub_category=SubCategory.APPRECIATION,
        sentiment=Sentiment.POSITIVE,
        themes=[],
        priority=Priority.LOW,
        confidence=90,
        summary="s",
    )

    body = admin_client.post("/feedback", json={"raw_text": "I love this product!"}).json()

    assert "thank you" in body["acknowledgement"].lower()


def test_acknowledgement_critical_priority_overrides_category_template(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.INCIDENT,
        sub_category=SubCategory.FEATURE_REQUEST,
        sentiment=Sentiment.NEGATIVE,
        themes=[],
        priority=Priority.CRITICAL,
        confidence=95,
        summary="s",
    )

    body = admin_client.post("/feedback", json={"raw_text": "Everything is down!"}).json()

    assert "critical" in body["acknowledgement"].lower()


def test_acknowledgement_falls_back_to_generic_on_low_confidence(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.GENERAL_FEEDBACK,
        sub_category=SubCategory.QUESTION,
        sentiment=Sentiment.NEUTRAL,
        themes=[],
        priority=Priority.LOW,
        confidence=10,
        summary="s",
    )

    body = admin_client.post("/feedback", json={"raw_text": "??"}).json()

    assert body["acknowledgement"] == "Thanks for your feedback - we've received it and a team member will take a closer look."


def test_acknowledgement_present_even_when_classification_fails(admin_client, mock_ai):
    mock_ai["classify"].side_effect = RuntimeError("OpenAI is down")

    body = admin_client.post("/feedback", json={"raw_text": "Anything at all."}).json()

    assert body["acknowledgement"] is not None
