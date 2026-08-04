from app.ai.schemas import FeedbackClassification
from app.database.models import MainCategory, Priority, Sentiment, SubCategory

SUBMITTER_FACING_FIELDS = {
    "id",
    "raw_text",
    "status",
    "acknowledgement",
    "admin_response",
    "admin_response_at",
    "attachments",
    "source",
    "property_id",
    "property_name",
    "property_city",
    "booking_id",
    "overall_rating",
    "cleanliness_rating",
    "communication_rating",
    "checkin_rating",
    "location_rating",
    "value_rating",
    "guest_decision",
    "created_at",
    "updated_at",
}

STAFF_ONLY_FIELDS = {
    "main_category",
    "sub_category",
    "sentiment",
    "priority",
    "confidence",
    "summary",
    "recommended_action",
    "themes",
    "tags",
    "internal_notes",
    "user_id",
    "submitter_user_id_legacy",
    "name",
    "email",
    "version",
    "device",
    "browser",
    "platform",
    "root_cause",
    "business_impact",
    "executive_summary",
    "preventive_recommendation",
    "responsible_team",
    "sla_due_at",
    "sla_breached",
    "duplicate_of_feedback_id",
    "escalated",
    "escalated_at",
}


def test_submitter_response_never_includes_staff_fields(user_client, mock_ai):
    response = user_client.post("/feedback", json={"raw_text": "The apartment was filthy when we arrived."})

    assert response.status_code == 201
    body = response.json()
    assert STAFF_ONLY_FIELDS.isdisjoint(body.keys())
    assert set(body.keys()) == SUBMITTER_FACING_FIELDS


def test_submitter_list_response_never_includes_staff_fields(user_client, mock_ai):
    user_client.post("/feedback", json={"raw_text": "The apartment was filthy when we arrived."})

    response = user_client.get("/feedback")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert STAFF_ONLY_FIELDS.isdisjoint(body[0].keys())


def test_host_response_never_includes_staff_fields(host_client, mock_ai):
    response = host_client.post("/feedback", json={"raw_text": "A guest left the kitchen a mess."})

    assert response.status_code == 201
    body = response.json()
    assert STAFF_ONLY_FIELDS.isdisjoint(body.keys())
    assert set(body.keys()) == SUBMITTER_FACING_FIELDS


def test_guest_can_only_see_own_feedback(client, mock_ai):
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


def test_host_can_only_see_own_feedback(client, mock_ai):
    client.post(
        "/auth/register",
        json={"email": "host-owner@example.com", "password": "test-password-123", "role": "HOST"},
    )
    owned_id = client.post("/feedback", json={"raw_text": "My own listing feedback."}).json()["id"]
    client.post("/auth/logout")

    other = client.post(
        "/auth/register",
        json={"email": "other-host@example.com", "password": "test-password-123", "role": "HOST"},
    )
    assert other.status_code == 201

    response = client.get(f"/feedback/{owned_id}")
    assert response.status_code == 403

    listed = client.get("/feedback").json()
    assert listed == []


def test_all_staff_roles_can_see_any_users_feedback(
    client, admin_client, ops_manager_client, product_manager_client, exec_client, mock_ai
):
    client.post("/auth/register", json={"email": "owner@example.com", "password": "test-password-123"})
    feedback_id = client.post("/feedback", json={"raw_text": "Some feedback."}).json()["id"]

    for staff in [admin_client, ops_manager_client, product_manager_client, exec_client]:
        response = staff.get(f"/feedback/{feedback_id}")
        assert response.status_code == 200
        assert response.json()["id"] == feedback_id

        list_response = staff.get("/feedback")
        assert list_response.status_code == 200
        assert any(item["id"] == feedback_id for item in list_response.json())


def test_all_staff_roles_can_view_analytics_and_reports(
    admin_client, ops_manager_client, product_manager_client, exec_client, mock_ai
):
    for staff in [admin_client, ops_manager_client, product_manager_client, exec_client]:
        assert staff.get("/analytics").status_code == 200
        assert staff.get("/themes").status_code == 200
        assert staff.get("/reports/weekly").status_code == 200


def test_bulk_uploaded_feedback_is_invisible_to_users(admin_client, user_client, mock_ai):
    admin_client.post("/bulk-upload", json={"items": [{"raw_text": "Imported historical feedback."}]})

    response = user_client.get("/feedback")

    assert response.status_code == 200
    assert response.json() == []


def test_guest_forbidden_from_staff_only_routes(user_client, mock_ai):
    assert user_client.get("/analytics").status_code == 403
    assert user_client.get("/themes").status_code == 403
    assert user_client.get("/reports/weekly").status_code == 403
    assert user_client.get("/feedback/export/csv").status_code == 403
    assert user_client.get("/feedback/export/pdf").status_code == 403
    assert user_client.post("/bulk-upload", json={"items": [{"raw_text": "x"}]}).status_code == 403


def test_manager_roles_can_patch_bulk_upload_and_export(admin_client, ops_manager_client, mock_ai):
    for manager in [admin_client, ops_manager_client]:
        feedback_id = manager.post("/feedback", json={"raw_text": "Something to manage."}).json()["id"]

        patch_response = manager.patch(f"/feedback/{feedback_id}", json={"status": "Resolved"})
        assert patch_response.status_code == 200

        bulk_response = manager.post("/bulk-upload", json={"items": [{"raw_text": "Imported item."}]})
        assert bulk_response.status_code == 201

        assert manager.get("/feedback/export/csv").status_code == 200
        assert manager.get("/feedback/export/pdf").status_code == 200


def test_view_only_staff_roles_get_403_on_write_routes(
    admin_client, product_manager_client, exec_client, mock_ai
):
    feedback_id = admin_client.post("/feedback", json={"raw_text": "Something to manage."}).json()["id"]

    for staff in [product_manager_client, exec_client]:
        patch_response = staff.patch(f"/feedback/{feedback_id}", json={"status": "Resolved"})
        assert patch_response.status_code == 403

        bulk_response = staff.post("/bulk-upload", json={"items": [{"raw_text": "Imported item."}]})
        assert bulk_response.status_code == 403

        assert staff.get("/feedback/export/csv").status_code == 403
        assert staff.get("/feedback/export/pdf").status_code == 403


def test_unauthenticated_requests_are_rejected(client, mock_ai):
    assert client.post("/feedback", json={"raw_text": "x"}).status_code == 401
    assert client.get("/feedback").status_code == 401
    assert client.get("/feedback/1").status_code == 401
    assert client.get("/analytics").status_code == 401


def test_manager_updates_status_and_response_visible_to_submitter(client, admin_client, mock_ai):
    client.post("/auth/register", json={"email": "submitter@example.com", "password": "test-password-123"})
    feedback_id = client.post(
        "/feedback", json={"raw_text": "The check-in instructions were confusing."}
    ).json()["id"]

    patch_response = admin_client.patch(
        f"/feedback/{feedback_id}",
        json={"status": "Resolved", "admin_response": "We've updated the check-in guide, thanks for flagging this!"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "Resolved"

    submitter_view = client.get(f"/feedback/{feedback_id}").json()
    assert submitter_view["status"] == "Resolved"
    assert submitter_view["admin_response"] == "We've updated the check-in guide, thanks for flagging this!"
    assert submitter_view["admin_response_at"] is not None


def test_manager_update_assigns_tags_and_internal_notes(admin_client, mock_ai):
    feedback_id = admin_client.post(
        "/feedback", json={"raw_text": "Please add a pet-friendly search filter."}
    ).json()["id"]

    response = admin_client.patch(
        f"/feedback/{feedback_id}",
        json={"tags": ["product-roadmap", "search"], "internal_notes": "Flagged for the Q3 roadmap review."},
    )

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["tags"]) == ["product-roadmap", "search"]
    assert body["internal_notes"] == "Flagged for the Q3 roadmap review."


def test_guest_cannot_patch_feedback(user_client, mock_ai):
    feedback_id = user_client.post("/feedback", json={"raw_text": "Something."}).json()["id"]

    response = user_client.patch(f"/feedback/{feedback_id}", json={"status": "Resolved"})

    assert response.status_code == 403


def test_acknowledgement_uses_feature_request_template(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.SUPPORT_TICKET,
        sub_category=SubCategory.FEATURE_REQUESTS,
        sentiment=Sentiment.NEUTRAL,
        themes=[],
        priority=Priority.LOW,
        confidence=90,
        summary="s",
        recommended_action="Log the request with the product team.",
    )

    body = admin_client.post("/feedback", json={"raw_text": "Please add a pet-friendly search filter."}).json()

    assert "feature request" in body["acknowledgement"].lower()


def test_acknowledgement_uses_app_issues_template(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.SUPPORT_TICKET,
        sub_category=SubCategory.APP_ISSUES,
        sentiment=Sentiment.NEGATIVE,
        themes=[],
        priority=Priority.MEDIUM,
        confidence=90,
        summary="s",
        recommended_action="File a bug report with mobile engineering.",
    )

    body = admin_client.post("/feedback", json={"raw_text": "The app keeps crashing when I open messages."}).json()

    assert "thank you" in body["acknowledgement"].lower()


def test_acknowledgement_critical_priority_overrides_category_template(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.HOST_COMPLAINT,
        sub_category=SubCategory.SAFETY,
        sentiment=Sentiment.NEGATIVE,
        themes=[],
        priority=Priority.CRITICAL,
        confidence=95,
        summary="s",
        recommended_action="Escalate to Trust & Safety immediately.",
    )

    body = admin_client.post(
        "/feedback", json={"raw_text": "There's no working smoke detector and I'm terrified!"}
    ).json()

    assert "critical" in body["acknowledgement"].lower()


def test_acknowledgement_falls_back_to_generic_on_low_confidence(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.SUPPORT_TICKET,
        sub_category=SubCategory.BOOKING_EXPERIENCE,
        sentiment=Sentiment.NEUTRAL,
        themes=[],
        priority=Priority.LOW,
        confidence=10,
        summary="s",
        recommended_action="n/a",
    )

    body = admin_client.post("/feedback", json={"raw_text": "??"}).json()

    assert body["acknowledgement"] == "Thanks for your feedback - we've received it and a team member will take a closer look."


def test_acknowledgement_present_even_when_classification_fails(admin_client, mock_ai):
    mock_ai["classify"].side_effect = RuntimeError("OpenAI is down")

    body = admin_client.post("/feedback", json={"raw_text": "Anything at all."}).json()

    assert body["acknowledgement"] is not None
