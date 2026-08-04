from app.database.models import Feedback, MainCategory, Priority, ResponsibleTeam


def _seed_feedback(db_session, *, user_id, **overrides) -> Feedback:
    defaults = dict(
        raw_text="Some complaint.",
        user_id=user_id,
        main_category=MainCategory.HOST_COMPLAINT,
        responsible_team=ResponsibleTeam.HOST,
        priority=Priority.MEDIUM,
    )
    defaults.update(overrides)
    feedback = Feedback(**defaults)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_notification_created_when_admin_response_is_set(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback(db_session, user_id=me["id"])

    admin_client.patch(f"/feedback/{feedback.id}", json={"admin_response": "We're looking into it."})

    response = user_client.get("/notifications")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "new response" in body[0]["message"].lower()
    assert body[0]["read_at"] is None


def test_notification_created_when_resolved(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback(db_session, user_id=me["id"])

    admin_client.patch(f"/feedback/{feedback.id}", json={"status": "Resolved"})

    response = user_client.get("/notifications")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "resolved" in body[0]["message"].lower()


def test_resolved_and_response_in_one_call_sends_one_notification(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback(db_session, user_id=me["id"])

    admin_client.patch(
        f"/feedback/{feedback.id}", json={"status": "Resolved", "admin_response": "All fixed now."}
    )

    body = user_client.get("/notifications").json()
    assert len(body) == 1
    assert "resolved" in body[0]["message"].lower()


def test_no_notification_for_unrelated_field_changes(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback(db_session, user_id=me["id"])

    admin_client.patch(f"/feedback/{feedback.id}", json={"priority": "High"})

    assert user_client.get("/notifications").json() == []


def test_no_notification_for_anonymous_bulk_imported_item(admin_client, db_session):
    feedback = _seed_feedback(db_session, user_id=None)

    response = admin_client.patch(f"/feedback/{feedback.id}", json={"admin_response": "Noted."})

    assert response.status_code == 200  # no crash, just no recipient to notify


def test_mark_notification_read(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback(db_session, user_id=me["id"])
    admin_client.patch(f"/feedback/{feedback.id}", json={"status": "Resolved"})
    notification_id = user_client.get("/notifications").json()[0]["id"]

    response = user_client.post(f"/notifications/{notification_id}/read")

    assert response.status_code == 200
    assert response.json()["read_at"] is not None

    unread = user_client.get("/notifications", params={"unread_only": "true"}).json()
    assert unread == []


def test_cannot_mark_someone_elses_notification_read(user_client, host_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback(db_session, user_id=me["id"])
    admin_client.patch(f"/feedback/{feedback.id}", json={"status": "Resolved"})
    notification_id = user_client.get("/notifications").json()[0]["id"]

    response = host_client.post(f"/notifications/{notification_id}/read")

    assert response.status_code == 403


def test_unknown_notification_returns_404(user_client):
    response = user_client.post("/notifications/999999/read")

    assert response.status_code == 404
