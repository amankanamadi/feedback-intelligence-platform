from __future__ import annotations

import logging

from app.ai.prompt_builder import PROMPT_INJECTION_GUARD, build_messages, format_retrieved_context
from app.ai.schemas import FeedbackClassification
from app.ai.structured_output import get_structured_completion
from app.database.models import MainCategory, Priority, Sentiment, SubCategory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI system that classifies customer feedback for a SaaS product.

Classify each piece of feedback into exactly one main category and one sub-category
from the taxonomy below, detect its sentiment, extract 1-5 short recurring themes,
assign a priority based on business impact and urgency, estimate your confidence
(0-100), and write a one-sentence summary.

Main Category: Incident
  Sub Categories: Product Bug, Application Crash, Login Issue, Payment Failure,
  Performance Issue, Security Issue, Data Loss, Integration Failure

Main Category: Service Request
  Sub Categories: Feature Request, UI/UX Improvement, Documentation Request,
  API Enhancement, Accessibility Improvement, New Integration

Main Category: General Feedback
  Sub Categories: Appreciation, Complaint, Pricing Feedback, Customer Support,
  Question, Suggestion

Sentiment must be one of: Positive, Neutral, Negative.
Priority must be one of: Low, Medium, High, Critical.

Sentiment guidance for tricky cases:
- Sarcasm/irony: judge the underlying intent from context, not just
  individual words. "Great, another crash right before my deadline" is
  Negative despite containing the word "great" - the context (repeated
  failure, bad timing) reveals frustration, not praise.
- Mixed sentiment: when feedback expresses both a complaint and a
  compliment, choose the sentiment that reflects the customer's primary,
  current disposition - often the outcome or most recent point they make,
  not a mechanical average. "Support was slow to respond but fixed my
  issue perfectly, I'm happy now" is Positive (positive outcome, current
  state); "The feature works but honestly the constant bugs are
  exhausting" is Negative (the complaint is the dominant point).
- Do not let surface-level positive or negative words override the actual
  meaning and context of the message.
""" + PROMPT_INJECTION_GUARD


def _example(main_category, sub_category, sentiment, themes, priority, confidence, summary) -> str:
    return FeedbackClassification(
        main_category=main_category,
        sub_category=sub_category,
        sentiment=sentiment,
        themes=themes,
        priority=priority,
        confidence=confidence,
        summary=summary,
    ).model_dump_json()


FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (
        "The dashboard has been really slow when loading reports for the past week.",
        _example(
            MainCategory.INCIDENT,
            SubCategory.PERFORMANCE_ISSUE,
            Sentiment.NEGATIVE,
            ["Slow Dashboard", "Performance"],
            Priority.MEDIUM,
            95,
            "Customer reports slow dashboard performance.",
        ),
    ),
    (
        "It would be great if we could export our reports directly to Excel.",
        _example(
            MainCategory.SERVICE_REQUEST,
            SubCategory.FEATURE_REQUEST,
            Sentiment.NEUTRAL,
            ["Excel Export", "Reporting"],
            Priority.LOW,
            90,
            "Customer requests the ability to export reports to Excel.",
        ),
    ),
    (
        "Your support team resolved my billing issue within minutes. Amazing service!",
        _example(
            MainCategory.GENERAL_FEEDBACK,
            SubCategory.APPRECIATION,
            Sentiment.POSITIVE,
            ["Support Quality", "Billing"],
            Priority.LOW,
            97,
            "Customer praises fast and effective support for a billing issue.",
        ),
    ),
    (
        "Oh wonderful, the app crashed again right when I was about to save my work. "
        "Just perfect timing as always.",
        _example(
            MainCategory.INCIDENT,
            SubCategory.APPLICATION_CRASH,
            Sentiment.NEGATIVE,
            ["App Crash", "Lost Work"],
            Priority.HIGH,
            88,
            "Customer sarcastically reports a recurring app crash that risked losing unsaved work.",
        ),
    ),
    (
        "The new checkout flow had a rocky start with a few bugs, but the team pushed a fix "
        "within a day and everything's working smoothly now. Really happy with the responsiveness.",
        _example(
            MainCategory.GENERAL_FEEDBACK,
            SubCategory.APPRECIATION,
            Sentiment.POSITIVE,
            ["Quick Bug Fix", "Support Responsiveness"],
            Priority.LOW,
            88,
            "Customer appreciates the team's fast fix of an early checkout bug and is satisfied "
            "with the outcome.",
        ),
    ),
]


def classify_feedback(
    raw_text: str, similar_examples: list[dict] | None = None
) -> FeedbackClassification:
    context_block = format_retrieved_context(similar_examples or [])
    if context_block:
        logger.info("Retrieved RAG context for classification:\n%s", context_block)

    user_content = f"{context_block}\n\n{raw_text}" if context_block else raw_text
    messages = build_messages(SYSTEM_PROMPT, user_content, FEW_SHOT_EXAMPLES)
    return get_structured_completion(messages, FeedbackClassification)
