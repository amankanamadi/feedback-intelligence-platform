"""AI output validation against the real OpenAI API.

These tests are marked `live`: they cost money, are not fully deterministic,
and are excluded from the default `pytest` run (see pytest.ini). Run them
explicitly with:

    pytest -m live tests/test_ai_live.py

They check that real responses are well-formed and sane, not that
classification is *accurate* against a labeled dataset - that's the job of
scripts/evaluate_accuracy.py.
"""

import pytest

from app.ai.classification import classify_feedback
from app.database.models import MainCategory, Priority, Sentiment, SubCategory

pytestmark = pytest.mark.live


def test_classify_feedback_returns_well_formed_output():
    result = classify_feedback("The app crashes every time I try to upload a large file.")

    assert isinstance(result.main_category, MainCategory)
    assert isinstance(result.sub_category, SubCategory)
    assert isinstance(result.sentiment, Sentiment)
    assert isinstance(result.priority, Priority)
    assert 0 <= result.confidence <= 100
    assert 1 <= len(result.themes) <= 5
    assert all(isinstance(theme, str) and theme.strip() for theme in result.themes)
    assert result.summary.strip() != ""


def test_classify_feedback_obvious_incident_is_negative_incident():
    result = classify_feedback("Your app crashed and I lost all my unsaved work, this is unacceptable.")

    assert result.main_category == MainCategory.INCIDENT
    assert result.sentiment == Sentiment.NEGATIVE


def test_classify_feedback_obvious_appreciation_is_positive():
    result = classify_feedback("Thank you so much, your support team fixed my issue instantly!")

    assert result.main_category == MainCategory.GENERAL_FEEDBACK
    assert result.sentiment == Sentiment.POSITIVE
