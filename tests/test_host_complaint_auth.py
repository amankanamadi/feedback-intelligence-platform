from datetime import date

from app.database.models import Booking, BookingStatus, Property, PropertyType


def _seed_property(db_session, *, host_id=None, **overrides) -> Property:
    defaults = dict(
        name="Host Complaint Test Villa", host_name="Test Host", city="Miami", country="USA",
        property_type=PropertyType.ENTIRE_HOME, host_id=host_id,
    )
    defaults.update(overrides)
    property_row = Property(**defaults)
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)
    return property_row


def _seed_booking(db_session, *, guest_id: int, property_id: int, **overrides) -> Booking:
    defaults = dict(
        confirmation_code="ABNB-HOST-COMPLAINT-0001",
        guest_id=guest_id,
        property_id=property_id,
        check_in_date=date(2026, 5, 1),
        check_out_date=date(2026, 5, 5),
        status=BookingStatus.UPCOMING,
    )
    defaults.update(overrides)
    booking = Booking(**defaults)
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


def test_host_can_submit_complaint_for_their_own_property_booking(user_client, host_client, mock_ai, db_session):
    guest = user_client.get("/auth/me").json()
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    booking = _seed_booking(db_session, guest_id=guest["id"], property_id=property_row.id)

    response = host_client.post(
        "/feedback", json={"raw_text": "This guest left the kitchen a total mess.", "booking_id": booking.id}
    )

    assert response.status_code == 201
    assert response.json()["property_id"] == property_row.id


def test_host_cannot_submit_a_review_for_their_own_property_booking(user_client, host_client, mock_ai, db_session):
    guest = user_client.get("/auth/me").json()
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    booking = _seed_booking(
        db_session, guest_id=guest["id"], property_id=property_row.id, status=BookingStatus.COMPLETED
    )

    response = host_client.post(
        "/feedback",
        json={
            "raw_text": "Rating my own place, why not.",
            "booking_id": booking.id,
            "overall_rating": 5,
            "cleanliness_rating": 5,
            "communication_rating": 5,
            "checkin_rating": 5,
            "location_rating": 5,
            "value_rating": 5,
        },
    )

    assert response.status_code == 403


def test_unrelated_host_cannot_submit_complaint_for_someone_elses_property_booking(
    user_client, host_client, mock_ai, db_session
):
    guest = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=None)  # not owned by host_client
    booking = _seed_booking(db_session, guest_id=guest["id"], property_id=property_row.id)

    response = host_client.post(
        "/feedback", json={"raw_text": "Reporting a mess I have no business reporting.", "booking_id": booking.id}
    )

    assert response.status_code == 403
