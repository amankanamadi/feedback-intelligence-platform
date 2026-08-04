from app.core.security import hash_password
from app.database import crud
from app.database.models import Feedback, MainCategory, Priority, Property, PropertyType, ResponsibleTeam, Role


def _seed_property(db_session, *, host_id=None, **overrides) -> Property:
    defaults = dict(
        name="Host Queue Test Villa", host_name="Test Host", city="Seattle", country="USA",
        property_type=PropertyType.ENTIRE_HOME, host_id=host_id,
    )
    defaults.update(overrides)
    property_row = Property(**defaults)
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)
    return property_row


def _seed_feedback(db_session, *, property_id, responsible_team=None, main_category=MainCategory.HOST_COMPLAINT, **overrides) -> Feedback:
    defaults = dict(
        raw_text="Some feedback.",
        property_id=property_id,
        main_category=main_category,
        responsible_team=responsible_team,
        priority=Priority.MEDIUM,
    )
    defaults.update(overrides)
    feedback = Feedback(**defaults)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_host_queue_route_not_shadowed_by_feedback_id_route(host_client):
    """Regression guard: /feedback/host-queue must be matched as its own
    route, not swallowed by GET /feedback/{feedback_id} trying (and
    failing) to parse "host-queue" as an integer id."""
    response = host_client.get("/feedback/host-queue")

    assert response.status_code == 200


def test_host_queue_returns_only_items_routed_to_host(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    routed = _seed_feedback(db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.HOST)
    _seed_feedback(
        db_session, property_id=property_row.id, responsible_team=ResponsibleTeam.TRUST_AND_SAFETY
    )
    _seed_feedback(db_session, property_id=property_row.id, responsible_team=None, main_category=MainCategory.GUEST_REVIEW)

    response = host_client.get("/feedback/host-queue")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == routed.id


def test_host_queue_scoped_to_the_correct_host(host_client, db_session):
    other_host = crud.create_user(
        db_session, email="other-host-queue@example.com",
        hashed_password=hash_password("test-password-123"), role=Role.HOST,
    )
    other_property = _seed_property(db_session, host_id=other_host.id)
    _seed_feedback(db_session, property_id=other_property.id, responsible_team=ResponsibleTeam.HOST)

    response = host_client.get("/feedback/host-queue")

    assert response.status_code == 200
    assert response.json() == []


def test_guest_forbidden_from_host_queue(user_client):
    response = user_client.get("/feedback/host-queue")

    assert response.status_code == 403


def test_staff_forbidden_from_host_queue(admin_client):
    response = admin_client.get("/feedback/host-queue")

    assert response.status_code == 403


def test_host_queue_item_shape_excludes_staff_only_fields(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    _seed_feedback(
        db_session,
        property_id=property_row.id,
        responsible_team=ResponsibleTeam.HOST,
        internal_notes="staff eyes only",
    )

    response = host_client.get("/feedback/host-queue")

    assert response.status_code == 200
    body = response.json()[0]
    assert "internal_notes" not in body
    assert "tags" not in body
    assert "confidence" not in body
    assert "executive_summary" not in body
    assert body["main_category"] == "Host Complaint"
    assert body["responsible_team"] == "Host"
