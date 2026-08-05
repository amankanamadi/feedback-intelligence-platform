from app.core.security import hash_password
from app.database import crud
from app.database.models import Feedback, MainCategory, Property, PropertyType, ResponsibleTeam, Role


def _seed_property(db_session, *, host_id=None, **overrides) -> Property:
    defaults = dict(
        name="Host Reviews Test Villa", host_name="Test Host", city="Seattle", country="USA",
        property_type=PropertyType.ENTIRE_HOME, host_id=host_id,
    )
    defaults.update(overrides)
    property_row = Property(**defaults)
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)
    return property_row


def _seed_feedback(db_session, *, property_id, main_category, **overrides) -> Feedback:
    defaults = dict(raw_text="Some feedback.", property_id=property_id, main_category=main_category)
    defaults.update(overrides)
    feedback = Feedback(**defaults)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_host_reviews_route_not_shadowed_by_feedback_id_route(host_client):
    response = host_client.get("/feedback/host-reviews")

    assert response.status_code == 200


def test_host_reviews_returns_only_guest_reviews_for_own_properties(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    review = _seed_feedback(db_session, property_id=property_row.id, main_category=MainCategory.GUEST_REVIEW)
    _seed_feedback(
        db_session,
        property_id=property_row.id,
        main_category=MainCategory.HOST_COMPLAINT,
        responsible_team=ResponsibleTeam.HOST,
    )
    _seed_feedback(db_session, property_id=property_row.id, main_category=MainCategory.SUPPORT_TICKET)

    response = host_client.get("/feedback/host-reviews")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == review.id
    assert items[0]["main_category"] == "Guest Review"


def test_host_reviews_scoped_to_the_correct_host(host_client, db_session):
    other_host = crud.create_user(
        db_session, email="other-host-reviews@example.com",
        hashed_password=hash_password("test-password-123"), role=Role.HOST,
    )
    other_property = _seed_property(db_session, host_id=other_host.id)
    _seed_feedback(db_session, property_id=other_property.id, main_category=MainCategory.GUEST_REVIEW)

    response = host_client.get("/feedback/host-reviews")

    assert response.status_code == 200
    assert response.json() == []


def test_guest_forbidden_from_host_reviews(user_client):
    response = user_client.get("/feedback/host-reviews")

    assert response.status_code == 403


def test_staff_forbidden_from_host_reviews(admin_client):
    response = admin_client.get("/feedback/host-reviews")

    assert response.status_code == 403


def test_host_reviews_item_shape_excludes_staff_only_fields(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    _seed_feedback(
        db_session,
        property_id=property_row.id,
        main_category=MainCategory.GUEST_REVIEW,
        overall_rating=5,
        internal_notes="staff eyes only",
    )

    response = host_client.get("/feedback/host-reviews")

    assert response.status_code == 200
    body = response.json()[0]
    assert "internal_notes" not in body
    assert "tags" not in body
    assert "confidence" not in body
    assert body["overall_rating"] == 5
