"""Rule-based acknowledgement generation.

Deterministic template lookup, not a second LLM call - acknowledgements
are returned synchronously in the same request as classification, and the
category/priority/confidence input space is small and fixed, so a second
OpenAI round trip would double submission latency/cost for no real
benefit. Unlike the AI steps in app/api/feedback.py, this can't fail, so
it needs no try/except - it degrades to a generic message by falling
through the lookups below, never by raising.
"""
from __future__ import annotations

from typing import Optional

from app.database.models import Priority, SubCategory

LOW_CONFIDENCE_THRESHOLD = 60

GENERIC_FALLBACK = "Thank you for your feedback. Our team has received it and will review it shortly."
LOW_CONFIDENCE_FALLBACK = (
    "Thanks for your feedback - we've received it and a team member will take a closer look."
)
CRITICAL_OVERRIDE = (
    "This has been flagged as critical and escalated immediately to our team for urgent attention."
)
HIGH_PRIORITY_OVERRIDE = "We've flagged this as high priority and our team will follow up as soon as possible."

_SUBCATEGORY_TEMPLATES: dict[SubCategory, str] = {
    # Guest Review subcategories
    SubCategory.CLEANLINESS: (
        "Thanks for letting us know about the cleanliness issue - we've flagged this with the "
        "property's cleaning team and someone will follow up shortly."
    ),
    SubCategory.WIFI: (
        "Sorry about the WiFi trouble - we've passed this along to the host and our team will "
        "help get it sorted."
    ),
    SubCategory.CHECK_IN: (
        "Sorry you had trouble checking in - we've notified the host and our team is looking "
        "into it right away."
    ),
    SubCategory.AMENITIES: (
        "Thanks for flagging the issue with the listing's amenities - we've shared this with the "
        "host and our team will follow up."
    ),
    SubCategory.HOST_COMMUNICATION: (
        "Thanks for sharing this - we've passed your feedback about the host's communication "
        "along to our team."
    ),
    # Host Complaint subcategories
    SubCategory.SAFETY: (
        "Thank you for reporting this safety concern. Our Trust & Safety team has been notified "
        "and will investigate immediately."
    ),
    SubCategory.MAINTENANCE: (
        "Thanks for reporting this - our team has logged the maintenance issue and will follow "
        "up on next steps shortly."
    ),
    # Support Ticket subcategories
    SubCategory.BOOKING_EXPERIENCE: (
        "Sorry about the trouble with your booking - our support team has received your report "
        "and will follow up soon."
    ),
    SubCategory.PAYMENTS: (
        "We've received your payment report and a specialist will follow up with you shortly."
    ),
    SubCategory.REFUNDS: (
        "We've received your refund request and our payments team will follow up with an update soon."
    ),
    SubCategory.APP_ISSUES: (
        "Thank you for reporting this issue. Our engineering team has received your report and "
        "will investigate it as soon as possible."
    ),
    SubCategory.FEATURE_REQUESTS: (
        "Thank you for your suggestion! Your feature request has been recorded and will be "
        "reviewed by our product team during future planning."
    ),
}


def generate_acknowledgement(
    *,
    sub_category: Optional[SubCategory],
    priority: Optional[Priority],
    confidence: Optional[int],
) -> str:
    if confidence is None or confidence < LOW_CONFIDENCE_THRESHOLD:
        return LOW_CONFIDENCE_FALLBACK
    if priority == Priority.CRITICAL:
        return CRITICAL_OVERRIDE
    if priority == Priority.HIGH:
        return HIGH_PRIORITY_OVERRIDE
    if sub_category is None:
        return GENERIC_FALLBACK
    return _SUBCATEGORY_TEMPLATES.get(sub_category, GENERIC_FALLBACK)
