from unittest.mock import MagicMock

import pytest

from app.ai.schemas import WeeklyNarrative
from app.database import crud
from app.database.models import MainCategory, Priority, Sentiment, SubCategory

FIXED_NARRATIVE = WeeklyNarrative(
    executive_summary="Test summary.",
    key_wins=["Win one."],
    key_concerns=["Concern one."],
    recommended_actions=["Action one."],
    emerging_risks=["Risk one."],
    forecast="Stable outlook.",
)


@pytest.fixture
def mock_narrative(monkeypatch):
    import app.api.reports as reports_module

    narrative_mock = MagicMock(return_value=FIXED_NARRATIVE)
    monkeypatch.setattr(reports_module, "generate_weekly_narrative", narrative_mock)
    return narrative_mock


def test_weekly_report_empty_db(admin_client, mock_narrative):
    response = admin_client.get("/reports/weekly")

    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["total_feedback"] == 0
    assert body["top_concerns"] == []
    assert body["positive_highlights"] == []
    assert body["executive_summary"] == "Test summary."
    assert body["key_wins"] == ["Win one."]
    assert body["emerging_risks"] == ["Risk one."]
    assert body["forecast"] == "Stable outlook."


def test_weekly_report_reflects_seeded_data(admin_client, db_session, mock_narrative):
    urgent = crud.create_feedback(db_session, raw_text="No working smoke detector, this is a safety hazard.")
    crud.apply_classification(
        db_session,
        urgent,
        main_category=MainCategory.HOST_COMPLAINT,
        sub_category=SubCategory.SAFETY,
        sentiment=Sentiment.NEGATIVE,
        priority=Priority.CRITICAL,
        confidence=95,
        summary="Safety hazard.",
        theme_names=["Safety"],
        recommended_action="Escalate to Trust & Safety immediately.",
    )

    happy = crud.create_feedback(db_session, raw_text="Loving this listing, the host was amazing!")
    crud.apply_classification(
        db_session,
        happy,
        main_category=MainCategory.GUEST_REVIEW,
        sub_category=SubCategory.HOST_COMMUNICATION,
        sentiment=Sentiment.POSITIVE,
        priority=Priority.LOW,
        confidence=95,
        summary="Appreciation.",
        theme_names=["Host Praise"],
        recommended_action="Share the positive feedback with the host.",
    )

    response = admin_client.get("/reports/weekly")

    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["total_feedback"] == 2
    assert len(body["top_concerns"]) == 1
    assert body["top_concerns"][0]["raw_text"] == "No working smoke detector, this is a safety hazard."
    assert len(body["positive_highlights"]) == 1
    assert body["positive_highlights"][0]["raw_text"] == "Loving this listing, the host was amazing!"


def test_weekly_report_excludes_positive_non_review_from_highlights(admin_client, db_session, mock_narrative):
    """Regression check: a Support Ticket that got mistagged Positive
    sentiment (e.g. a politely-worded feature request born from a
    frustrating cancellation) must never surface as a "positive
    highlight" - only genuine Guest Review wins should."""
    mistagged = crud.create_feedback(db_session, raw_text="No easy way to message the host after cancelling.")
    crud.apply_classification(
        db_session,
        mistagged,
        main_category=MainCategory.SUPPORT_TICKET,
        sub_category=SubCategory.FEATURE_REQUESTS,
        sentiment=Sentiment.POSITIVE,
        priority=Priority.LOW,
        confidence=80,
        summary="Guest suggests a communication feature after a cancellation.",
        theme_names=["Feature Request"],
        recommended_action="Log with product team.",
    )

    response = admin_client.get("/reports/weekly")

    assert response.status_code == 200
    assert response.json()["positive_highlights"] == []


def test_weekly_report_degrades_gracefully_when_narrative_fails(admin_client, mock_narrative):
    mock_narrative.side_effect = RuntimeError("OpenAI is down")

    response = admin_client.get("/reports/weekly")

    assert response.status_code == 200
    body = response.json()
    assert body["executive_summary"] == "Executive summary unavailable."
    assert body["key_wins"] == []
    assert body["emerging_risks"] == []
    assert body["forecast"] == "Forecast unavailable."


@pytest.mark.parametrize(
    "client_fixture,expected_role",
    [
        ("admin_client", "SUPPORT_MANAGER"),
        ("ops_manager_client", "OPS_MANAGER"),
        ("product_manager_client", "PRODUCT_MANAGER"),
        ("exec_client", "EXEC"),
        ("trust_safety_client", "TRUST_SAFETY"),
    ],
)
def test_weekly_report_passes_the_callers_own_role(client_fixture, expected_role, mock_narrative, request):
    from app.database.models import Role

    staff_client = request.getfixturevalue(client_fixture)

    response = staff_client.get("/reports/weekly")

    assert response.status_code == 200
    assert mock_narrative.call_args.kwargs["role"] == Role[expected_role]
