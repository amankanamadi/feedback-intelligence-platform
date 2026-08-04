from app.database.models import Feedback, MainCategory, Priority, ResponsibleTeam


def _seed_feedback_with_response(db_session, *, user_id, **overrides) -> Feedback:
    defaults = dict(
        raw_text="A complaint awaiting a decision.",
        user_id=user_id,
        main_category=MainCategory.HOST_COMPLAINT,
        responsible_team=ResponsibleTeam.HOST,
        priority=Priority.MEDIUM,
        admin_response="Here's what we're doing to fix it.",
    )
    defaults.update(overrides)
    feedback = Feedback(**defaults)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_guest_can_accept_resolution(user_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback_with_response(db_session, user_id=me["id"])

    response = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Accepted"})

    assert response.status_code == 200
    body = response.json()
    assert body["guest_decision"] == "Accepted"
    assert body["status"] == "Resolved"


def test_guest_can_reject_resolution_and_it_escalates(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback_with_response(db_session, user_id=me["id"])

    response = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Rejected"})

    assert response.status_code == 200
    body = response.json()
    assert body["guest_decision"] == "Rejected"
    assert body["status"] == "In Review"

    staff_view = admin_client.get(f"/feedback/{feedback.id}").json()
    assert staff_view["escalated"] is True
    assert staff_view["escalated_at"] is not None


def test_decision_requires_a_response_first(user_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback_with_response(db_session, user_id=me["id"], admin_response=None)

    response = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Accepted"})

    assert response.status_code == 422


def test_decision_is_one_shot_until_a_new_response(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback_with_response(db_session, user_id=me["id"])

    first = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Rejected"})
    assert first.status_code == 200

    second = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Accepted"})
    assert second.status_code == 422

    # A follow-up response resets guest_decision, re-opening the choice.
    patch = admin_client.patch(f"/feedback/{feedback.id}", json={"admin_response": "Here's a new plan."})
    assert patch.status_code == 200
    assert patch.json()["guest_decision"] is None

    third = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Accepted"})
    assert third.status_code == 200


def test_other_users_decision_forbidden(user_client, host_client, db_session):
    other_guest = host_client.get("/auth/me").json()
    feedback = _seed_feedback_with_response(db_session, user_id=other_guest["id"])

    response = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Accepted"})

    assert response.status_code == 403


def test_pending_decision_rejected(user_client, db_session):
    me = user_client.get("/auth/me").json()
    feedback = _seed_feedback_with_response(db_session, user_id=me["id"])

    response = user_client.post(f"/feedback/{feedback.id}/decision", json={"decision": "Pending"})

    assert response.status_code == 422
