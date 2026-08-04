from unittest.mock import MagicMock

from app.ai.schemas import WeeklyNarrative
from app.ai.weekly_report import ROLE_SYSTEM_PROMPTS, generate_weekly_narrative
from app.analytics.service import get_analytics_summary
from app.database.models import Role

ALL_STAFF_ROLES = {
    Role.OPS_MANAGER,
    Role.SUPPORT_MANAGER,
    Role.PRODUCT_MANAGER,
    Role.TRUST_SAFETY,
    Role.EXEC,
}


def test_every_staff_role_has_a_system_prompt():
    assert set(ROLE_SYSTEM_PROMPTS.keys()) == ALL_STAFF_ROLES


def test_every_role_prompt_is_distinct():
    assert len(set(ROLE_SYSTEM_PROMPTS.values())) == len(ROLE_SYSTEM_PROMPTS)


def test_generate_weekly_narrative_uses_the_prompt_matching_the_given_role(db_session, monkeypatch):
    import app.ai.weekly_report as weekly_report_module

    metrics = get_analytics_summary(db_session)
    fake_narrative = WeeklyNarrative(
        executive_summary="s", key_wins=[], key_concerns=[], recommended_actions=[],
        emerging_risks=[], forecast="f",
    )
    completion_mock = MagicMock(return_value=fake_narrative)
    monkeypatch.setattr(weekly_report_module, "get_structured_completion", completion_mock)

    generate_weekly_narrative(metrics, [], [], role=Role.TRUST_SAFETY)

    messages = completion_mock.call_args.args[0]
    assert messages[0]["content"] == ROLE_SYSTEM_PROMPTS[Role.TRUST_SAFETY]
    assert messages[0]["content"] != ROLE_SYSTEM_PROMPTS[Role.EXEC]
