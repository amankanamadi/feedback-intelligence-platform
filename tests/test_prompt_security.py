from app.ai import classification, weekly_report
from app.ai.prompt_builder import PROMPT_INJECTION_GUARD


def test_classification_system_prompt_includes_injection_guard():
    assert PROMPT_INJECTION_GUARD in classification.SYSTEM_PROMPT


def test_weekly_report_system_prompt_includes_injection_guard():
    assert PROMPT_INJECTION_GUARD in weekly_report.SYSTEM_PROMPT
