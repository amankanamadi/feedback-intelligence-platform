import pytest

from app.database.models import MainCategory, ResponsibleTeam, SubCategory
from app.services.routing import reconcile_main_category, route_to_team

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


RECONCILE_CASES = [
    # (given main_category, sub_category, expected corrected main_category)
    (MainCategory.GUEST_REVIEW, SubCategory.MAINTENANCE, MainCategory.HOST_COMPLAINT),
    (MainCategory.GUEST_REVIEW, SubCategory.SAFETY, MainCategory.HOST_COMPLAINT),
    (MainCategory.GUEST_REVIEW, SubCategory.PAYMENTS, MainCategory.SUPPORT_TICKET),
    (MainCategory.HOST_COMPLAINT, SubCategory.CLEANLINESS, MainCategory.GUEST_REVIEW),
    (MainCategory.SUPPORT_TICKET, SubCategory.FEATURE_REQUESTS, MainCategory.SUPPORT_TICKET),
]


@pytest.mark.parametrize("main_category,sub_category,expected", RECONCILE_CASES)
def test_reconcile_main_category_corrects_contradictions(main_category, sub_category, expected):
    assert reconcile_main_category(main_category, sub_category) == expected


@pytest.mark.parametrize(
    "main_category,sub_category",
    [
        (MainCategory.GUEST_REVIEW, SubCategory.CLEANLINESS),
        (MainCategory.HOST_COMPLAINT, SubCategory.SAFETY),
        (MainCategory.SUPPORT_TICKET, SubCategory.REFUNDS),
    ],
)
def test_reconcile_main_category_is_a_no_op_when_already_consistent(main_category, sub_category):
    assert reconcile_main_category(main_category, sub_category) == main_category
