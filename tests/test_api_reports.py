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
)


@pytest.fixture
def mock_narrative(monkeypatch):
    import app.api.reports as reports_module

    narrative_mock = MagicMock(return_value=FIXED_NARRATIVE)
    monkeypatch.setattr(reports_module, "generate_weekly_narrative", narrative_mock)
    return narrative_mock


def test_weekly_report_empty_db(client, mock_narrative):
    response = client.get("/reports/weekly")

    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["total_feedback"] == 0
    assert body["top_concerns"] == []
    assert body["positive_highlights"] == []
    assert body["executive_summary"] == "Test summary."
    assert body["key_wins"] == ["Win one."]


def test_weekly_report_reflects_seeded_data(client, db_session, mock_narrative):
    urgent = crud.create_feedback(db_session, raw_text="Critical login outage.")
    crud.apply_classification(
        db_session,
        urgent,
        main_category=MainCategory.INCIDENT,
        sub_category=SubCategory.LOGIN_ISSUE,
        sentiment=Sentiment.NEGATIVE,
        priority=Priority.CRITICAL,
        confidence=95,
        summary="Login outage.",
        theme_names=["Login"],
    )

    happy = crud.create_feedback(db_session, raw_text="Loving the new feature!")
    crud.apply_classification(
        db_session,
        happy,
        main_category=MainCategory.GENERAL_FEEDBACK,
        sub_category=SubCategory.APPRECIATION,
        sentiment=Sentiment.POSITIVE,
        priority=Priority.LOW,
        confidence=95,
        summary="Appreciation.",
        theme_names=["Feature Love"],
    )

    response = client.get("/reports/weekly")

    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["total_feedback"] == 2
    assert len(body["top_concerns"]) == 1
    assert body["top_concerns"][0]["raw_text"] == "Critical login outage."
    assert len(body["positive_highlights"]) == 1
    assert body["positive_highlights"][0]["raw_text"] == "Loving the new feature!"


def test_weekly_report_degrades_gracefully_when_narrative_fails(client, mock_narrative):
    mock_narrative.side_effect = RuntimeError("OpenAI is down")

    response = client.get("/reports/weekly")

    assert response.status_code == 200
    body = response.json()
    assert body["executive_summary"] == "Executive summary unavailable."
    assert body["key_wins"] == []
