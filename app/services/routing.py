"""Rule-based complaint routing and main/sub-category reconciliation.

Both mappings here are deterministic sub-category lookups, not an AI
decision - which team is responsible for a given issue type, and which
main category a given sub-category belongs to, are fixed business facts
(same rationale as app/services/acknowledgement.py). Guest Review
sub-categories are intentionally absent from _ROUTING: routing is only
ever computed for Host Complaint / Support Ticket (see
app/api/feedback.py), so they would never be looked up there.
"""
from __future__ import annotations

from typing import Optional

from app.database.models import MainCategory, ResponsibleTeam, SubCategory

_ROUTING: dict[SubCategory, ResponsibleTeam] = {
    SubCategory.SAFETY: ResponsibleTeam.TRUST_AND_SAFETY,
    SubCategory.MAINTENANCE: ResponsibleTeam.HOST,
    SubCategory.BOOKING_EXPERIENCE: ResponsibleTeam.CUSTOMER_SUPPORT,
    SubCategory.PAYMENTS: ResponsibleTeam.PAYMENTS,
    SubCategory.REFUNDS: ResponsibleTeam.FINANCE,
    SubCategory.APP_ISSUES: ResponsibleTeam.ENGINEERING,
    SubCategory.FEATURE_REQUESTS: ResponsibleTeam.PRODUCT,
}


def route_to_team(sub_category: SubCategory) -> Optional[ResponsibleTeam]:
    return _ROUTING.get(sub_category)


# Each sub_category belongs to exactly one main_category (see SubCategory's
# own grouping comments in app/database/models.py, and the same grouping
# taught to the classifier in app/ai/classification.py's SYSTEM_PROMPT).
_SUB_CATEGORY_MAIN_CATEGORY: dict[SubCategory, MainCategory] = {
    SubCategory.CLEANLINESS: MainCategory.GUEST_REVIEW,
    SubCategory.WIFI: MainCategory.GUEST_REVIEW,
    SubCategory.CHECK_IN: MainCategory.GUEST_REVIEW,
    SubCategory.AMENITIES: MainCategory.GUEST_REVIEW,
    SubCategory.HOST_COMMUNICATION: MainCategory.GUEST_REVIEW,
    SubCategory.SAFETY: MainCategory.HOST_COMPLAINT,
    SubCategory.MAINTENANCE: MainCategory.HOST_COMPLAINT,
    SubCategory.BOOKING_EXPERIENCE: MainCategory.SUPPORT_TICKET,
    SubCategory.PAYMENTS: MainCategory.SUPPORT_TICKET,
    SubCategory.REFUNDS: MainCategory.SUPPORT_TICKET,
    SubCategory.APP_ISSUES: MainCategory.SUPPORT_TICKET,
    SubCategory.FEATURE_REQUESTS: MainCategory.SUPPORT_TICKET,
}


def reconcile_main_category(main_category: MainCategory, sub_category: SubCategory) -> MainCategory:
    """Corrects a self-contradictory classification (e.g. main_category=
    Guest Review paired with sub_category=Maintenance) before it's stored.
    The prompt teaches the model the correct pairing, but nothing enforces
    it structurally, and a wrong main_category here would silently skip
    responsible_team routing for a genuinely actionable complaint (routing
    only ever runs for non-Guest-Review items) - the sub_category's fixed
    taxonomy group is authoritative, not the model's separately-guessed
    main_category. Only meaningful for non-review submissions; a stay
    review's main_category is forced to Guest Review by the booking
    workflow itself and must never be overridden here (see
    app/api/feedback.py's _process_feedback_submission).
    """
    return _SUB_CATEGORY_MAIN_CATEGORY.get(sub_category, main_category)
