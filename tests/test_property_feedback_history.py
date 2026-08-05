from app.core.security import hash_password
from app.database import crud
from app.database.models import Feedback, MainCategory, Property, PropertyType, ResponsibleTeam, Role


def _seed_property(db_session, *, host_id=None, **overrides) -> Property:
    defaults = dict(
        name="Property History Test Villa", host_name="Test Host", city="Denver", country="USA",
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


def test_property_feedback_history_includes_reviews_and_complaints(host_client, db_session):
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    review = _seed_feedback(db_session, property_id=property_row.id, main_category=MainCategory.GUEST_REVIEW)
    complaint = _seed_feedback(
        db_session,
        property_id=property_row.id,
        main_category=MainCategory.HOST_COMPLAINT,
        responsible_team=ResponsibleTeam.HOST,
    )

    response = host_client.get(f"/feedback/property/{property_row.id}")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {review.id, complaint.id}


def test_property_feedback_history_404_for_unknown_property(host_client):
    response = host_client.get("/feedback/property/999999")

    assert response.status_code == 404


def test_property_feedback_history_403_for_property_not_owned(host_client, db_session):
    other_host = crud.create_user(
        db_session, email="other-host-property-history@example.com",
        hashed_password=hash_password("test-password-123"), role=Role.HOST,
    )
    other_property = _seed_property(db_session, host_id=other_host.id)

    response = host_client.get(f"/feedback/property/{other_property.id}")

    assert response.status_code == 403


def test_property_feedback_history_403_for_guest(user_client, db_session):
    property_row = _seed_property(db_session)

    response = user_client.get(f"/feedback/property/{property_row.id}")

    assert response.status_code == 403


def test_property_feedback_history_403_for_staff(admin_client, db_session):
    property_row = _seed_property(db_session)

    response = admin_client.get(f"/feedback/property/{property_row.id}")

    assert response.status_code == 403
