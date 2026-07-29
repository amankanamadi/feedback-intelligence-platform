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
    # Bug Report / Incident-flavored subcategories
    SubCategory.PRODUCT_BUG: (
        "Thank you for reporting this issue. Our engineering team has received your report "
        "and will investigate it as soon as possible."
    ),
    SubCategory.APPLICATION_CRASH: (
        "Thank you for reporting this issue. Our engineering team has received your report "
        "and will investigate it as soon as possible."
    ),
    SubCategory.LOGIN_ISSUE: (
        "Sorry you're having trouble logging in - our team has been notified and is looking into it."
    ),
    SubCategory.PAYMENT_FAILURE: (
        "We've received your billing report and a specialist will follow up with you shortly."
    ),
    SubCategory.PERFORMANCE_ISSUE: "Thanks for flagging the performance issue - we're looking into it.",
    SubCategory.SECURITY_ISSUE: (
        "Thank you for reporting this security concern. Our team has been notified and will "
        "investigate immediately."
    ),
    SubCategory.DATA_LOSS: (
        "Thank you for reporting this issue. Our engineering team has received your report "
        "and will investigate it as soon as possible."
    ),
    SubCategory.INTEGRATION_FAILURE: (
        "Thank you for reporting this issue. Our engineering team has received your report "
        "and will investigate it as soon as possible."
    ),
    # Service Request subcategories
    SubCategory.FEATURE_REQUEST: (
        "Thank you for your suggestion! Your feature request has been recorded and will be "
        "reviewed by our product team during future planning."
    ),
    SubCategory.UI_UX_IMPROVEMENT: (
        "Thank you for your suggestion! Your feedback has been recorded and will be reviewed "
        "by our product team during future planning."
    ),
    SubCategory.DOCUMENTATION_REQUEST: (
        "Thanks for the suggestion - we've passed this along to the team responsible for our documentation."
    ),
    SubCategory.API_ENHANCEMENT: (
        "Thank you for your suggestion! Your feature request has been recorded and will be "
        "reviewed by our product team during future planning."
    ),
    SubCategory.ACCESSIBILITY_IMPROVEMENT: (
        "Thank you for your suggestion! Your feedback has been recorded and will be reviewed "
        "by our product team during future planning."
    ),
    SubCategory.NEW_INTEGRATION: (
        "Thank you for your suggestion! Your feature request has been recorded and will be "
        "reviewed by our product team during future planning."
    ),
    # General Feedback subcategories
    SubCategory.APPRECIATION: "Thank you for your kind words! Your feedback motivates our team to continue improving.",
    SubCategory.COMPLAINT: "We're sorry to hear about your experience. Your concern has been recorded and our team will carefully review it.",
    SubCategory.PRICING_FEEDBACK: "Thank you for sharing your thoughts on pricing - we've passed this along to the team.",
    SubCategory.CUSTOMER_SUPPORT: "Thank you for the feedback on your support experience - we've shared it with the team.",
    SubCategory.QUESTION: "Thanks for reaching out - our team will get back to you with an answer soon.",
    SubCategory.SUGGESTION: (
        "Thank you for your suggestion! Your feedback has been recorded and will be reviewed "
        "by our product team during future planning."
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
