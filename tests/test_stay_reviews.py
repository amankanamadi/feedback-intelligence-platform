from datetime import date

from sqlalchemy import select

from app.ai.schemas import FeedbackClassification
from app.database.models import (
    Booking,
    BookingStatus,
    MainCategory,
    Notification,
    Priority,
    Property,
    PropertyType,
    Sentiment,
    SubCategory,
)

FULL_RATINGS = {
    "overall_rating": 4,
    "cleanliness_rating": 5,
    "communication_rating": 4,
    "checkin_rating": 3,
    "location_rating": 5,
    "value_rating": 4,
}


def _seed_property(db_session, **overrides) -> Property:
    defaults = dict(
        name="Sunset Loft", host_name="Michael Chen", city="Austin", country="USA",
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
        confirmation_code="ABNB-REVIEW-0001",
        guest_id=guest_id,
        property_id=property_id,
        check_in_date=date(2026, 5, 1),
        check_out_date=date(2026, 5, 5),
        status=BookingStatus.COMPLETED,
    )
    defaults.update(overrides)
    booking = Booking(**defaults)
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


def test_partial_ratings_rejected(user_client, mock_ai):
    response = user_client.post(
        "/feedback",
        json={"raw_text": "Great stay overall.", "overall_rating": 5, "cleanliness_rating": 5},
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_ratings_without_booking_id_rejected(user_client, mock_ai):
    response = user_client.post("/feedback", json={"raw_text": "Great stay overall.", **FULL_RATINGS})

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_rating_out_of_range_rejected(user_client, mock_ai, db_session):
    me = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking = _seed_booking(db_session, guest_id=me["id"], property_id=property_row.id)

    bad_ratings = {**FULL_RATINGS, "overall_rating": 6}
    response = user_client.post(
        "/feedback", json={"raw_text": "Great stay overall.", "booking_id": booking.id, **bad_ratings}
    )

    assert response.status_code == 422
    mock_ai["classify"].assert_not_called()


def test_review_for_nonexistent_booking_returns_404(user_client, mock_ai):
    response = user_client.post(
        "/feedback", json={"raw_text": "Great stay overall.", "booking_id": 999999, **FULL_RATINGS}
    )

    assert response.status_code == 404
    mock_ai["classify"].assert_not_called()


def test_review_for_another_guests_booking_forbidden(user_client, host_client, mock_ai, db_session):
    other_guest = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking = _seed_booking(db_session, guest_id=other_guest["id"], property_id=property_row.id)

    response = user_client.post(
        "/feedback", json={"raw_text": "Great stay overall.", "booking_id": booking.id, **FULL_RATINGS}
    )

    assert response.status_code == 403
    mock_ai["classify"].assert_not_called()


def test_review_rejected_for_upcoming_booking(user_client, mock_ai, db_session):
    me = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking = _seed_booking(
        db_session, guest_id=me["id"], property_id=property_row.id, status=BookingStatus.UPCOMING
    )

    response = user_client.post(
        "/feedback", json={"raw_text": "Great stay overall.", "booking_id": booking.id, **FULL_RATINGS}
    )

    assert response.status_code == 422
    assert "completed" in response.json()["detail"].lower()
    mock_ai["classify"].assert_not_called()


def test_valid_stay_review_succeeds_and_forces_guest_review_category(
    user_client, admin_client, mock_ai, db_session
):
    # The AI mock deliberately returns a non-review category, to prove the
    # workflow (ratings + a completed booking) - not the AI - decides
    # main_category for a stay review.
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.HOST_COMPLAINT,
        sub_category=SubCategory.MAINTENANCE,
        sentiment=Sentiment.NEGATIVE,
        themes=["Cleanliness"],
        priority=Priority.HIGH,
        confidence=90,
        summary="Guest reports a cleanliness issue.",
        recommended_action="Escalate to housekeeping.",
    )

    me = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking = _seed_booking(db_session, guest_id=me["id"], property_id=property_row.id)

    response = user_client.post(
        "/feedback",
        json={
            "raw_text": "The place was clean and the host was great, though check-in was confusing.",
            "booking_id": booking.id,
            "property_id": 999999,  # deliberately wrong/bogus - the booking's property must win
            **FULL_RATINGS,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["booking_id"] == booking.id
    assert body["property_id"] == property_row.id  # derived from the booking, not the bogus client value
    for field, value in FULL_RATINGS.items():
        assert body[field] == value

    # main_category/sub_category are staff-only fields - check via the staff view.
    staff_view = admin_client.get(f"/feedback/{body['id']}").json()
    assert staff_view["main_category"] == "Guest Review"
    assert staff_view["sub_category"] == "Maintenance"  # AI's sub_category is still honored
    assert staff_view["sentiment"] == "Negative"


def test_duplicate_review_for_same_booking_rejected(user_client, mock_ai, db_session):
    me = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking = _seed_booking(db_session, guest_id=me["id"], property_id=property_row.id)

    first = user_client.post(
        "/feedback", json={"raw_text": "Great stay overall.", "booking_id": booking.id, **FULL_RATINGS}
    )
    assert first.status_code == 201

    second = user_client.post(
        "/feedback", json={"raw_text": "Submitting again for some reason.", "booking_id": booking.id, **FULL_RATINGS}
    )

    assert second.status_code == 422
    assert "already been submitted" in second.json()["detail"].lower()


def test_property_average_rating_reflects_only_guest_ratings(user_client, mock_ai, db_session):
    me = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)
    booking_1 = _seed_booking(
        db_session, guest_id=me["id"], property_id=property_row.id, confirmation_code="ABNB-A"
    )
    booking_2 = _seed_booking(
        db_session, guest_id=me["id"], property_id=property_row.id, confirmation_code="ABNB-B"
    )

    user_client.post(
        "/feedback",
        json={"raw_text": "First stay, loved it.", "booking_id": booking_1.id, **{**FULL_RATINGS, "overall_rating": 5}},
    )
    user_client.post(
        "/feedback",
        json={"raw_text": "Second stay, just okay.", "booking_id": booking_2.id, **{**FULL_RATINGS, "overall_rating": 3}},
    )
    # A plain complaint (no ratings) on the same property must never affect the average.
    user_client.post("/feedback", json={"raw_text": "Unrelated complaint, no ratings here."})

    response = user_client.get("/properties")

    assert response.status_code == 200
    matching = [p for p in response.json() if p["id"] == property_row.id]
    assert len(matching) == 1
    assert matching[0]["average_rating"] == 4.0  # (5 + 3) / 2, unaffected by the un-rated complaint


def test_stay_review_notifies_the_property_host(user_client, host_client, mock_ai, db_session):
    guest = user_client.get("/auth/me").json()
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    booking = _seed_booking(db_session, guest_id=guest["id"], property_id=property_row.id)

    response = user_client.post(
        "/feedback", json={"raw_text": "Loved this place!", "booking_id": booking.id, **FULL_RATINGS}
    )

    assert response.status_code == 201
    notifications = list(db_session.scalars(select(Notification).where(Notification.user_id == host["id"])))
    assert len(notifications) == 1
    assert property_row.name in notifications[0].message
    assert notifications[0].link == "/app/host"


def test_stay_review_for_hostless_property_creates_no_notification(user_client, mock_ai, db_session):
    guest = user_client.get("/auth/me").json()
    property_row = _seed_property(db_session)  # no host_id
    booking = _seed_booking(db_session, guest_id=guest["id"], property_id=property_row.id)

    response = user_client.post(
        "/feedback", json={"raw_text": "Loved this place!", "booking_id": booking.id, **FULL_RATINGS}
    )

    assert response.status_code == 201
    assert list(db_session.scalars(select(Notification))) == []


def test_plain_complaint_does_not_notify_the_host(user_client, host_client, mock_ai, db_session):
    """A booking-tied complaint (no ratings) is a real case a host may need
    to act on via the complaint queue/notifications-from-PATCH flow - it
    must not also fire the review-only notification."""
    guest = user_client.get("/auth/me").json()
    host = host_client.get("/auth/me").json()
    property_row = _seed_property(db_session, host_id=host["id"])
    booking = _seed_booking(db_session, guest_id=guest["id"], property_id=property_row.id)

    response = user_client.post(
        "/feedback", json={"raw_text": "The WiFi didn't work the whole stay.", "booking_id": booking.id}
    )

    assert response.status_code == 201
    assert list(db_session.scalars(select(Notification).where(Notification.user_id == host["id"]))) == []


def test_plain_feedback_without_ratings_still_works(user_client, mock_ai):
    """Regression check: the existing non-review submission path is
    completely unaffected by the stay-review workflow."""
    response = user_client.post("/feedback", json={"raw_text": "The WiFi was down the whole stay."})

    assert response.status_code == 201
    body = response.json()
    assert body["booking_id"] is None
    assert body["overall_rating"] is None
