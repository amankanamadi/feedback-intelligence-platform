from __future__ import annotations

from app.ai.prompt_builder import build_messages
from app.ai.schemas import FeedbackClassification
from app.ai.structured_output import get_structured_completion
from app.database.models import MainCategory, Priority, Sentiment, SubCategory

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
"""


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
]


def classify_feedback(raw_text: str) -> FeedbackClassification:
    messages = build_messages(SYSTEM_PROMPT, raw_text, FEW_SHOT_EXAMPLES)
    return get_structured_completion(messages, FeedbackClassification)
