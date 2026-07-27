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


def test_classify_feedback_sarcasm_is_negative_not_positive():
    result = classify_feedback(
        "Oh fantastic, the export button broke again right before my big presentation. "
        "Just what I needed today."
    )

    assert result.sentiment == Sentiment.NEGATIVE


def test_classify_feedback_negative_wording_with_positive_outcome_is_positive():
    # The overall verdict must be explicit ("all set up and loving it now"),
    # not just implied by describing a good resolution - an ambiguous
    # version of this case (annoyance + good resolution with no stated
    # verdict) is a genuinely defensible split decision, not a clear-cut
    # Positive, and shouldn't be asserted as one.
    result = classify_feedback(
        "The onboarding process was frustrating with several confusing steps, but the "
        "support team walked me through everything patiently and now I'm all set up "
        "and loving the product."
    )

    assert result.sentiment == Sentiment.POSITIVE
