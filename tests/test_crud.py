from app.database import crud
from app.database.models import FeedbackSource, MainCategory, Priority, Property, PropertyType, Sentiment, SubCategory


def test_create_feedback_without_themes(db_session):
    feedback = crud.create_feedback(db_session, raw_text="The listing is not as described.")

    assert feedback.id is not None
    assert feedback.raw_text == "The listing is not as described."
    assert feedback.main_category is None
    assert feedback.themes == []


def test_create_feedback_with_themes(db_session):
    feedback = crud.create_feedback(
        db_session, raw_text="Dirty apartment.", theme_names=["Dirty Apartment", "Cleaning Quality"]
    )

    theme_names = {t.name for t in feedback.themes}
    assert theme_names == {"Dirty Apartment", "Cleaning Quality"}


def test_create_feedback_logs_warning_on_duplicate_text(db_session, caplog):
    crud.create_feedback(db_session, raw_text="Duplicate me.")

    with caplog.at_level("WARNING"):
        second = crud.create_feedback(db_session, raw_text="Duplicate me.")

    assert second.id is not None
    assert "duplicate" in caplog.text.lower()


def test_create_feedback_dedupes_duplicate_theme_names(db_session):
    feedback = crud.create_feedback(
        db_session,
        raw_text="Dirty apartment, really dirty.",
        theme_names=["Dirty Apartment", "Dirty Apartment", "Cleaning Quality"],
    )

    assert sorted(t.name for t in feedback.themes) == ["Cleaning Quality", "Dirty Apartment"]


def _seed_property(db_session) -> Property:
    property_row = Property(
        name="Sunny Loft",
        host_name="Jordan Lee",
        city="Austin",
        country="USA",
        property_type=PropertyType.ENTIRE_HOME,
    )
    db_session.add(property_row)
    db_session.commit()
    return property_row


def test_create_feedback_persists_metadata_fields(db_session):
    property_row = _seed_property(db_session)

    feedback = crud.create_feedback(
        db_session,
        raw_text="Can't check in - the door code isn't working.",
        submitter_user_id_legacy="user-42",
        name="Jordan Lee",
        email="jordan@example.com",
        source=FeedbackSource.MOBILE_APP,
        property_id=property_row.id,
        version="3.2.1",
        device="iPhone 15",
        browser="Safari",
        platform="iOS",
    )

    assert feedback.submitter_user_id_legacy == "user-42"
    assert feedback.name == "Jordan Lee"
    assert feedback.email == "jordan@example.com"
    assert feedback.source == FeedbackSource.MOBILE_APP
    assert feedback.property_id == property_row.id
    assert feedback.version == "3.2.1"
    assert feedback.device == "iPhone 15"
    assert feedback.browser == "Safari"
    assert feedback.platform == "iOS"


def test_create_feedback_metadata_fields_default_to_none(db_session):
    feedback = crud.create_feedback(db_session, raw_text="No metadata here.")

    assert feedback.submitter_user_id_legacy is None
    assert feedback.name is None
    assert feedback.email is None
    assert feedback.source is None
    assert feedback.property_id is None


def test_apply_classification_dedupes_duplicate_theme_names(db_session):
    feedback = crud.create_feedback(db_session, raw_text="The WiFi never works.")

    updated = crud.apply_classification(
        db_session,
        feedback,
        main_category=MainCategory.GUEST_REVIEW,
        sub_category=SubCategory.WIFI,
        sentiment=Sentiment.NEGATIVE,
        priority=Priority.HIGH,
        confidence=90,
        summary="Guest reports the WiFi never works.",
        theme_names=["Weak WiFi", "Weak WiFi"],
        recommended_action="Send WiFi troubleshooting guide.",
    )

    assert [t.name for t in updated.themes] == ["Weak WiFi"]


def test_get_or_create_theme_deduplicates(db_session):
    first = crud.get_or_create_theme(db_session, "Dirty Apartment")
    second = crud.get_or_create_theme(db_session, "Dirty Apartment")

    assert first.id == second.id


def test_apply_classification_updates_fields(db_session):
    feedback = crud.create_feedback(db_session, raw_text="The WiFi never works.")

    updated = crud.apply_classification(
        db_session,
        feedback,
        main_category=MainCategory.GUEST_REVIEW,
        sub_category=SubCategory.WIFI,
        sentiment=Sentiment.NEGATIVE,
        priority=Priority.HIGH,
        confidence=90,
        summary="Guest reports the WiFi never works.",
        theme_names=["Weak WiFi"],
        recommended_action="Send WiFi troubleshooting guide.",
    )

    assert updated.main_category == MainCategory.GUEST_REVIEW
    assert updated.sub_category == SubCategory.WIFI
    assert updated.sentiment == Sentiment.NEGATIVE
    assert updated.priority == Priority.HIGH
    assert updated.confidence == 90
    assert updated.recommended_action == "Send WiFi troubleshooting guide."
    assert [t.name for t in updated.themes] == ["Weak WiFi"]


def test_get_feedback_returns_none_for_missing_id(db_session):
    assert crud.get_feedback(db_session, 999_999) is None


def test_list_feedback_filters_by_main_category(db_session):
    guest_review = crud.create_feedback(db_session, raw_text="The apartment was filthy.")
    crud.apply_classification(
        db_session,
        guest_review,
        main_category=MainCategory.GUEST_REVIEW,
        sub_category=SubCategory.CLEANLINESS,
        sentiment=Sentiment.NEGATIVE,
        priority=Priority.HIGH,
        confidence=90,
        summary="Cleanliness complaint.",
        theme_names=[],
        recommended_action="Escalate to housekeeping.",
    )

    request = crud.create_feedback(db_session, raw_text="Please add a pet-friendly search filter.")
    crud.apply_classification(
        db_session,
        request,
        main_category=MainCategory.SUPPORT_TICKET,
        sub_category=SubCategory.FEATURE_REQUESTS,
        sentiment=Sentiment.NEUTRAL,
        priority=Priority.LOW,
        confidence=90,
        summary="Feature request.",
        theme_names=[],
        recommended_action="Log with product team.",
    )

    results = crud.list_feedback(db_session, main_category=MainCategory.GUEST_REVIEW)

    assert len(results) == 1
    assert results[0].id == guest_review.id


def test_list_feedback_search_matches_case_insensitively(db_session):
    crud.create_feedback(db_session, raw_text="The Apartment was dirty.")
    crud.create_feedback(db_session, raw_text="Unrelated feedback.")

    results = crud.list_feedback(db_session, search="apartment")

    assert len(results) == 1
    assert "Apartment" in results[0].raw_text


def test_list_feedback_respects_pagination(db_session):
    for i in range(5):
        crud.create_feedback(db_session, raw_text=f"Feedback {i}")

    page = crud.list_feedback(db_session, skip=2, limit=2)

    assert len(page) == 2


def test_list_feedback_filters_by_source(db_session):
    crud.create_feedback(db_session, raw_text="Via email.", source=FeedbackSource.EMAIL)
    crud.create_feedback(db_session, raw_text="Via the website.", source=FeedbackSource.WEBSITE)

    results = crud.list_feedback(db_session, source=FeedbackSource.EMAIL)

    assert len(results) == 1
    assert results[0].raw_text == "Via email."


def test_list_feedback_filters_by_property_id(db_session):
    property_a = _seed_property(db_session)
    property_b = Property(
        name="Cozy Studio", host_name="Alex Rivera", city="Denver", country="USA", property_type=PropertyType.PRIVATE_ROOM
    )
    db_session.add(property_b)
    db_session.commit()

    crud.create_feedback(db_session, raw_text="Feedback for Sunny Loft.", property_id=property_a.id)
    crud.create_feedback(db_session, raw_text="Feedback for Cozy Studio.", property_id=property_b.id)

    results = crud.list_feedback(db_session, property_id=property_a.id)

    assert len(results) == 1
    assert results[0].raw_text == "Feedback for Sunny Loft."


def test_list_properties_filters_by_search(db_session):
    _seed_property(db_session)
    db_session.add(
        Property(name="Cozy Studio", host_name="Alex Rivera", city="Denver", country="USA", property_type=PropertyType.PRIVATE_ROOM)
    )
    db_session.commit()

    results = crud.list_properties(db_session, search="sunny")

    assert len(results) == 1
    assert results[0].name == "Sunny Loft"


def test_list_properties_filters_by_city(db_session):
    _seed_property(db_session)
    db_session.add(
        Property(name="Cozy Studio", host_name="Alex Rivera", city="Denver", country="USA", property_type=PropertyType.PRIVATE_ROOM)
    )
    db_session.commit()

    results = crud.list_properties(db_session, city="denver")

    assert len(results) == 1
    assert results[0].name == "Cozy Studio"


def test_get_property_returns_none_for_missing_id(db_session):
    assert crud.get_property(db_session, 999_999) is None
