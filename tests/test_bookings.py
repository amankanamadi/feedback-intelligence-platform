from datetime import date

from app.database.models import Booking, BookingStatus, Property, PropertyType


def _seed_property(db_session, **overrides) -> Property:
    defaults = dict(
        name="Ocean Breeze Villa",
        host_name="Sarah Johnson",
        city="Malibu",
        country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    defaults.update(overrides)
    property_row = Property(**defaults)
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)
    return property_row


def _seed_booking(db_session, *, guest_id: int, property_id: int, **overrides) -> Booking:
    defaults = dict(
        confirmation_code="ABNB-TEST-0001",
        guest_id=guest_id,
        property_id=property_id,
        check_in_date=date(2026, 6, 1),
        check_out_date=date(2026, 6, 5),
        status=BookingStatus.COMPLETED,
    )
    defaults.update(overrides)
    booking = Booking(**defaults)
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


def test_guest_can_look_up_own_booking(user_client, db_session):
    me = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking = _seed_booking(db_session, guest_id=me["id"], property_id=property_row.id)

    response = user_client.get(f"/bookings/{booking.confirmation_code}")

    assert response.status_code == 200
    body = response.json()
    assert body["confirmation_code"] == booking.confirmation_code
    assert body["status"] == "Completed"
    assert body["property"]["name"] == "Ocean Breeze Villa"


def test_guest_cannot_look_up_another_guests_booking(user_client, host_client, db_session):
    other_guest = host_client.get("/auth/me").json()  # a different account, standing in for "someone else"
    property_row = _seed_property(db_session)
    booking = _seed_booking(db_session, guest_id=other_guest["id"], property_id=property_row.id)

    response = user_client.get(f"/bookings/{booking.confirmation_code}")

    assert response.status_code == 403


def test_staff_can_look_up_any_booking(user_client, admin_client, db_session):
    me = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking = _seed_booking(db_session, guest_id=me["id"], property_id=property_row.id)

    response = admin_client.get(f"/bookings/{booking.confirmation_code}")

    assert response.status_code == 200
    assert response.json()["confirmation_code"] == booking.confirmation_code


def test_unknown_confirmation_code_returns_404(user_client):
    response = user_client.get("/bookings/DOES-NOT-EXIST")

    assert response.status_code == 404


def test_booking_lookup_requires_authentication(client, db_session):
    response = client.get("/bookings/ABNB-TEST-0001")

    assert response.status_code == 401
