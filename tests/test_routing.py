import pytest

from app.database.models import ResponsibleTeam, SubCategory
from app.services.routing import route_to_team

ROUTING_CASES = [
    (SubCategory.SAFETY, ResponsibleTeam.TRUST_AND_SAFETY),
    (SubCategory.MAINTENANCE, ResponsibleTeam.HOST),
    (SubCategory.BOOKING_EXPERIENCE, ResponsibleTeam.CUSTOMER_SUPPORT),
    (SubCategory.PAYMENTS, ResponsibleTeam.PAYMENTS),
    (SubCategory.REFUNDS, ResponsibleTeam.FINANCE),
    (SubCategory.APP_ISSUES, ResponsibleTeam.ENGINEERING),
    (SubCategory.FEATURE_REQUESTS, ResponsibleTeam.PRODUCT),
]


@pytest.mark.parametrize("sub_category,expected_team", ROUTING_CASES)
def test_route_to_team_maps_each_actionable_subcategory(sub_category, expected_team):
    assert route_to_team(sub_category) == expected_team


@pytest.mark.parametrize(
    "sub_category",
    [
        SubCategory.CLEANLINESS,
        SubCategory.WIFI,
        SubCategory.CHECK_IN,
        SubCategory.AMENITIES,
        SubCategory.HOST_COMMUNICATION,
    ],
)
def test_route_to_team_returns_none_for_guest_review_subcategories(sub_category):
    assert route_to_team(sub_category) is None
