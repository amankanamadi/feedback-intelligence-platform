"""Rule-based complaint routing.

Deterministic sub-category lookup, not an AI decision - which team is
responsible for a given issue type is a fixed business mapping, not
something that benefits from being left to the model's judgment (same
rationale as app/services/acknowledgement.py). Guest Review sub-categories
are intentionally absent from the mapping: routing is only ever computed
for Host Complaint / Support Ticket (see app/api/feedback.py), so they
would never be looked up here.
"""
from __future__ import annotations

from typing import Optional

from app.database.models import ResponsibleTeam, SubCategory

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
