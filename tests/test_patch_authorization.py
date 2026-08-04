from app.database import crud
from app.database.models import Feedback, MainCategory, Priority, Property, PropertyType, ResponsibleTeam


def _seed_property(db_session, *, host_id=None, **overrides) -> Property:
    defaults = dict(
        name="PATCH Auth Test Villa", host_name="Test Host", city="Denver", country="USA",
        property_type=PropertyType.ENTIRE_HOME, host_id=host_id,
    )
    defaults.update(overrides)
    property_row = Property(**defaults)
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)
    return property_row


def _seed_routed_feedback(db_session, *, property_id, responsible_team, user_id=None, **overrides) -> Feedback:
    defaults = dict(
        raw_text="A routed complaint.",
        property_id=property_id,
        user_id=user_id,
        main_category=MainCategory.HOST_COMPLAINT,
        responsible_team=responsible_team,
        priority=Priority.MEDIUM,
    )
    defaults.update(overrides)
    feedback = Feedback(**defaults)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_host_can_patch_status_and_admin_response_for_routed_item(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    feedback = _seed_routed_feedback(
        db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.HOST
    )

    response = host_client.patch(
        f"/feedback/{feedback.id}", json={"status": "In Progress", "admin_response": "We're on it."}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "In Progress"
    assert body["admin_response"] == "We're on it."
    # Host gets the thinner submitter shape, not staff/AI fields.
    assert "main_category" not in body
    assert "internal_notes" not in body


def test_host_gets_403_for_fields_beyond_status_and_admin_response(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    feedback = _seed_routed_feedback(
        db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.HOST
    )

    response = host_client.patch(f"/feedback/{feedback.id}", json={"priority": "Critical"})

    assert response.status_code == 403


def test_host_gets_403_for_trust_and_safety_routed_item_on_their_property(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    feedback = _seed_routed_feedback(
        db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.TRUST_AND_SAFETY
    )

    response = host_client.patch(f"/feedback/{feedback.id}", json={"status": "In Progress"})

    assert response.status_code == 403


def test_host_gets_403_for_property_they_dont_own(host_client, db_session):
    property_row = _seed_property(db_session, host_id=None)
    feedback = _seed_routed_feedback(
        db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.HOST
    )

    response = host_client.patch(f"/feedback/{feedback.id}", json={"status": "In Progress"})

    assert response.status_code == 403


def test_trust_safety_can_patch_item_routed_to_them(trust_safety_client, db_session):
    property_row = _seed_property(db_session)
    feedback = _seed_routed_feedback(
        db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.TRUST_AND_SAFETY
    )

    response = trust_safety_client.patch(
        f"/feedback/{feedback.id}", json={"status": "Resolved", "priority": "Low"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Resolved"


def test_trust_safety_gets_403_for_item_not_routed_to_them(trust_safety_client, db_session):
    property_row = _seed_property(db_session)
    feedback = _seed_routed_feedback(
        db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.HOST
    )

    response = trust_safety_client.patch(f"/feedback/{feedback.id}", json={"status": "Resolved"})

    assert response.status_code == 403


def test_reclassifying_to_guest_review_clears_routing_and_sla(admin_client, db_session):
    from datetime import datetime, timezone

    property_row = _seed_property(db_session)
    feedback = _seed_routed_feedback(
        db_session,
        property_id=property_row.id,
        responsible_team=ResponsibleTeam.HOST,
        sla_due_at=datetime.now(timezone.utc),
        escalated=True,
    )

    response = admin_client.patch(f"/feedback/{feedback.id}", json={"main_category": "Guest Review"})

    assert response.status_code == 200
    body = response.json()
    assert body["main_category"] == "Guest Review"
    assert body["responsible_team"] is None
    assert body["sla_due_at"] is None
    assert body["escalated"] is False
