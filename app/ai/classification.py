from __future__ import annotations

import logging

from app.ai.prompt_builder import PROMPT_INJECTION_GUARD, build_messages, format_retrieved_context
from app.ai.schemas import FeedbackClassification
from app.ai.structured_output import get_structured_completion
from app.database.models import MainCategory, Priority, Sentiment, SubCategory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI system that classifies guest and host feedback for an
Airbnb-style short-term rental platform.

Classify each piece of feedback into exactly one main category and one sub-category
from the taxonomy below, detect its sentiment, extract 1-5 short recurring themes,
assign a priority based on business impact and urgency, estimate your confidence
(0-100), write a one-sentence summary, and recommend a short, concrete next step
for the ops team to take (recommended_action).

Main Category: Guest Review
  Sub Categories: Cleanliness, WiFi, Check-in, Amenities, Host Communication

Main Category: Host Complaint
  Sub Categories: Safety, Maintenance

Main Category: Support Ticket
  Sub Categories: Booking Experience, Payments, Refunds, App Issues, Feature Requests

Sentiment must be one of: Positive, Neutral, Negative.
Priority must be one of: Low, Medium, High, Critical.

Sentiment guidance for tricky cases:
- Sarcasm/irony: judge the underlying intent from context, not just
  individual words. "Great, another cancellation right before my trip" is
  Negative despite containing the word "great" - the context (a last-minute
  cancellation disrupting travel plans) reveals frustration, not praise.
- Mixed sentiment: when feedback expresses both a complaint and a
  compliment, choose the sentiment that reflects the guest's or host's
  primary, current disposition - often the outcome or most recent point
  they make, not a mechanical average. "Host was slow to respond but fixed
  the check-in issue perfectly, I'm happy now" is Positive (positive
  outcome, current state); "The place was beautiful but the host never
  answers messages" is Negative (the unresponsiveness is the dominant
  complaint).
- Do not let surface-level positive or negative words override the actual
  meaning and context of the message.
""" + PROMPT_INJECTION_GUARD


def _example(
    main_category, sub_category, sentiment, themes, priority, confidence, summary, recommended_action
) -> str:
    return FeedbackClassification(
        main_category=main_category,
        sub_category=sub_category,
        sentiment=sentiment,
        themes=themes,
        priority=priority,
        confidence=confidence,
        summary=summary,
        recommended_action=recommended_action,
    ).model_dump_json()


FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (
        "The apartment was filthy when we arrived - there was dust everywhere, the "
        "bathroom hadn't been cleaned, and the sheets looked like they hadn't been washed.",
        _example(
            MainCategory.GUEST_REVIEW,
            SubCategory.CLEANLINESS,
            Sentiment.NEGATIVE,
            ["Dirty Apartment", "Cleaning Quality"],
            Priority.HIGH,
            94,
            "Guest reports the apartment was dirty on arrival, including an uncleaned "
            "bathroom and dirty sheets.",
            "Escalate to the property's housekeeping vendor for an immediate re-clean "
            "and follow up with the guest.",
        ),
    ),
    (
        "The WiFi barely works in this listing - I couldn't get a stable connection "
        "anywhere except right next to the router, which made it impossible to work "
        "remotely during my stay.",
        _example(
            MainCategory.GUEST_REVIEW,
            SubCategory.WIFI,
            Sentiment.NEGATIVE,
            ["Weak WiFi", "Remote Work"],
            Priority.MEDIUM,
            91,
            "Guest reports unreliable WiFi that only worked near the router, disrupting "
            "remote work.",
            "Send the guest the WiFi troubleshooting guide and ask the host to consider "
            "a mesh extender for the listing.",
        ),
    ),
    (
        "My check-in code didn't work when I arrived at 11pm and I was locked outside "
        "for over an hour before anyone answered - this is unacceptable.",
        _example(
            MainCategory.GUEST_REVIEW,
            SubCategory.CHECK_IN,
            Sentiment.NEGATIVE,
            ["Check-in Code Failure", "Late-Night Lockout"],
            Priority.HIGH,
            93,
            "Guest was locked out for over an hour after their check-in code failed to "
            "work late at night.",
            "Escalate to the host immediately to verify the smart lock code and offer "
            "the guest a partial refund for the delay.",
        ),
    ),
    (
        "Our host was a little slow to respond at first, but once the check-in issue "
        "came up she fixed it herself within minutes and even left us a welcome basket "
        "- I'm really happy with how it turned out.",
        _example(
            MainCategory.GUEST_REVIEW,
            SubCategory.HOST_COMMUNICATION,
            Sentiment.POSITIVE,
            ["Host Responsiveness", "Check-in Resolution"],
            Priority.LOW,
            89,
            "Guest was pleased with the host's quick resolution of a check-in issue and "
            "a thoughtful welcome gesture, despite a slow initial response.",
            "Share the positive feedback with the host; no further action needed.",
        ),
    ),
    (
        "As the host, I need to report that the smart lock on the front door has been "
        "broken for two days and anyone could walk in - I'm worried about my guests' safety.",
        _example(
            MainCategory.HOST_COMPLAINT,
            SubCategory.SAFETY,
            Sentiment.NEGATIVE,
            ["Broken Lock", "Guest Safety"],
            Priority.CRITICAL,
            96,
            "Host reports a broken smart lock leaving the property unsecured and current "
            "guests at risk.",
            "Escalate to Trust & Safety immediately and dispatch a locksmith to repair "
            "the lock today.",
        ),
    ),
    (
        "The last guests threw a party and left the living room a mess - a lamp is "
        "broken, there are stains on the couch, and a window screen is torn.",
        _example(
            MainCategory.HOST_COMPLAINT,
            SubCategory.MAINTENANCE,
            Sentiment.NEGATIVE,
            ["Property Damage", "Unauthorized Party"],
            Priority.HIGH,
            92,
            "Host reports significant property damage after guests held an unauthorized party.",
            "Open a damage claim, document the damage with photos, and charge the "
            "responsible guest's security deposit.",
        ),
    ),
    (
        "My trip was cancelled by the host and I still haven't received my refund after "
        "two weeks - can someone please look into this?",
        _example(
            MainCategory.SUPPORT_TICKET,
            SubCategory.REFUNDS,
            Sentiment.NEGATIVE,
            ["Overdue Refund", "Host Cancellation"],
            Priority.HIGH,
            90,
            "Guest is still waiting on a refund two weeks after a host-cancelled trip.",
            "Escalate to the payments team to process the overdue refund within 24 "
            "hours and notify the guest.",
        ),
    ),
    (
        "The app keeps crashing every time I try to open my messages with the host - "
        "I've reinstalled it twice and it still happens.",
        _example(
            MainCategory.SUPPORT_TICKET,
            SubCategory.APP_ISSUES,
            Sentiment.NEGATIVE,
            ["App Crash", "Messaging"],
            Priority.MEDIUM,
            90,
            "Guest reports the app repeatedly crashes when opening host messages, even "
            "after reinstalling.",
            "File a bug report with the mobile engineering team and ask the guest for "
            "their device model and OS version.",
        ),
    ),
    (
        "It would be so helpful if I could filter search results by pet-friendly "
        "listings that also have a pool - right now I have to check each listing one by one.",
        _example(
            MainCategory.SUPPORT_TICKET,
            SubCategory.FEATURE_REQUESTS,
            Sentiment.NEUTRAL,
            ["Search Filters", "Pet-Friendly"],
            Priority.LOW,
            88,
            "Guest requests the ability to filter search results by pet-friendly "
            "listings with a pool.",
            "Log the request with the product team as a candidate search filter enhancement.",
        ),
    ),
    (
        "Great, another cancellation right before my trip. Third time this has "
        "happened with this platform.",
        _example(
            MainCategory.SUPPORT_TICKET,
            SubCategory.BOOKING_EXPERIENCE,
            Sentiment.NEGATIVE,
            ["Last-Minute Cancellation", "Repeat Issue"],
            Priority.HIGH,
            87,
            "Guest sarcastically reports a last-minute booking cancellation, the third "
            "such incident.",
            "Escalate to the booking experience team to review the host's cancellation "
            "pattern and offer the guest rebooking assistance.",
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
