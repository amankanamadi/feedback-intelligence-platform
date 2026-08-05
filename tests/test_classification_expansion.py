from app.ai.schemas import FeedbackClassification
from app.database.models import MainCategory, Priority, ResponsibleTeam, Sentiment, SubCategory


def test_complaint_submission_populates_expanded_ai_fields_and_routing(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.HOST_COMPLAINT,
        sub_category=SubCategory.SAFETY,
        sentiment=Sentiment.NEGATIVE,
        themes=["Broken Lock"],
        priority=Priority.CRITICAL,
        confidence=96,
        summary="Host reports a broken smart lock.",
        recommended_action="Escalate to Trust & Safety immediately.",
        root_cause="The smart lock's hardware failed.",
        business_impact="Guests are physically unsafe.",
        executive_summary="An unsecured front door poses an immediate safety risk.",
        preventive_recommendation="Enroll locks in a monitored maintenance program.",
    )

    body = admin_client.post(
        "/feedback", json={"raw_text": "The smart lock on the front door is broken."}
    ).json()

    assert body["root_cause"] == "The smart lock's hardware failed."
    assert body["business_impact"] == "Guests are physically unsafe."
    assert body["executive_summary"] == "An unsecured front door poses an immediate safety risk."
    assert body["preventive_recommendation"] == "Enroll locks in a monitored maintenance program."
    assert body["responsible_team"] == "Trust & Safety"
    assert body["sla_due_at"] is not None
    assert body["sla_breached"] is False
    assert body["duplicate_of_feedback_id"] is None


def test_support_ticket_routes_to_engineering(admin_client, mock_ai):
    mock_ai["classify"].return_value = FeedbackClassification(
        main_category=MainCategory.SUPPORT_TICKET,
        sub_category=SubCategory.APP_ISSUES,
        sentiment=Sentiment.NEGATIVE,
        themes=["App Crash"],
        priority=Priority.MEDIUM,
        confidence=90,
        summary="Guest reports the app crashes.",
        recommended_action="File a bug report.",
        root_cause="A bug in the messaging screen.",
        business_impact="Blocks guest-host communication.",
        executive_summary="A reproducible crash is blocking messaging.",
        preventive_recommendation="Add crash reporting and regression tests.",
    )

    body = admin_client.post("/feedback", json={"raw_text": "The app keeps crashing."}).json()

    assert body["responsible_team"] == ResponsibleTeam.ENGINEERING.value
    assert body["sla_due_at"] is not None


def test_guest_review_never_gets_a_responsible_team_or_sla_clock(admin_client, mock_ai, db_session):
    from datetime import date

    from app.database.models import Booking, BookingStatus, Property, PropertyType

    property_row = Property(
        name="Expansion Test Loft", host_name="Test Host", city="Boston", country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)

    me = admin_client.get("/auth/me").json()
    booking = Booking(
        confirmation_code="ABNB-EXPANSION-0001",
        guest_id=me["id"],
        property_id=property_row.id,
        check_in_date=date(2026, 5, 1),
        check_out_date=date(2026, 5, 5),
        status=BookingStatus.COMPLETED,
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    body = admin_client.post(
        "/feedback",
        json={
            "raw_text": "Lovely stay overall.",
            "booking_id": booking.id,
            "cleanliness_rating": 5,
            "housekeeping_rating": 5,
            "amenities_rating": 5,
            "communication_rating": 5,
            "checkin_rating": 5,
            "location_rating": 5,
            "value_rating": 5,
        },
    ).json()

    assert body["responsible_team"] is None
    assert body["sla_due_at"] is None
