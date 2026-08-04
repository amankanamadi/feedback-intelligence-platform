from app.ai import classification, weekly_report
from app.ai.prompt_builder import PROMPT_INJECTION_GUARD


def test_classification_system_prompt_includes_injection_guard():
    assert PROMPT_INJECTION_GUARD in classification.SYSTEM_PROMPT


def test_weekly_report_system_prompts_include_injection_guard():
    # weekly_report.SYSTEM_PROMPT no longer exists - Phase 5 replaced the
    # single fixed prompt with one per staff role (ROLE_SYSTEM_PROMPTS);
    # every one of them must still carry the guard.
    assert weekly_report.ROLE_SYSTEM_PROMPTS
    for prompt in weekly_report.ROLE_SYSTEM_PROMPTS.values():
        assert PROMPT_INJECTION_GUARD in prompt
