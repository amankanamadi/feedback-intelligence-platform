from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.ai.schemas import FeedbackClassification
from app.ai.structured_output import StructuredCompletionError, get_structured_completion
from app.database.models import MainCategory, Priority, Sentiment, SubCategory


def test_feedback_classification_rejects_confidence_above_100():
    with pytest.raises(ValidationError):
        FeedbackClassification(
            main_category=MainCategory.INCIDENT,
            sub_category=SubCategory.PERFORMANCE_ISSUE,
            sentiment=Sentiment.NEGATIVE,
            themes=["Slow"],
            priority=Priority.MEDIUM,
            confidence=150,
            summary="s",
        )


def test_feedback_classification_rejects_confidence_below_0():
    with pytest.raises(ValidationError):
        FeedbackClassification(
            main_category=MainCategory.INCIDENT,
            sub_category=SubCategory.PERFORMANCE_ISSUE,
            sentiment=Sentiment.NEGATIVE,
            themes=["Slow"],
            priority=Priority.MEDIUM,
            confidence=-1,
            summary="s",
        )


def test_feedback_classification_allows_empty_themes():
    classification = FeedbackClassification(
        main_category=MainCategory.GENERAL_FEEDBACK,
        sub_category=SubCategory.QUESTION,
        sentiment=Sentiment.NEUTRAL,
        themes=[],
        priority=Priority.LOW,
        confidence=80,
        summary="s",
    )

    assert classification.themes == []


def _fake_client(refusal, parsed):
    message = MagicMock(refusal=refusal, parsed=parsed)
    choice = MagicMock(message=message)
    completion = MagicMock(choices=[choice])
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = completion
    return client


def test_get_structured_completion_raises_on_refusal(monkeypatch):
    fake_client = _fake_client(refusal="I can't help with that.", parsed=None)
    monkeypatch.setattr("app.ai.structured_output.get_openai_client", lambda: fake_client)

    with pytest.raises(StructuredCompletionError, match="refused"):
        get_structured_completion([{"role": "user", "content": "hi"}], FeedbackClassification)


def test_get_structured_completion_raises_when_parsed_is_none(monkeypatch):
    fake_client = _fake_client(refusal=None, parsed=None)
    monkeypatch.setattr("app.ai.structured_output.get_openai_client", lambda: fake_client)

    with pytest.raises(StructuredCompletionError, match="did not match"):
        get_structured_completion([{"role": "user", "content": "hi"}], FeedbackClassification)


def test_get_structured_completion_wraps_unexpected_exceptions(monkeypatch):
    client = MagicMock()
    client.beta.chat.completions.parse.side_effect = RuntimeError("connection reset")
    monkeypatch.setattr("app.ai.structured_output.get_openai_client", lambda: client)

    with pytest.raises(StructuredCompletionError, match="connection reset"):
        get_structured_completion([{"role": "user", "content": "hi"}], FeedbackClassification)
