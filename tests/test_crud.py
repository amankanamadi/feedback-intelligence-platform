from app.database import crud
from app.database.models import MainCategory, Priority, Sentiment, SubCategory


def test_create_feedback_without_themes(db_session):
    feedback = crud.create_feedback(db_session, raw_text="The app is slow.")

    assert feedback.id is not None
    assert feedback.raw_text == "The app is slow."
    assert feedback.main_category is None
    assert feedback.themes == []


def test_create_feedback_with_themes(db_session):
    feedback = crud.create_feedback(
        db_session, raw_text="Slow dashboard.", theme_names=["Slow Dashboard", "Performance"]
    )

    theme_names = {t.name for t in feedback.themes}
    assert theme_names == {"Slow Dashboard", "Performance"}


def test_create_feedback_logs_warning_on_duplicate_text(db_session, caplog):
    crud.create_feedback(db_session, raw_text="Duplicate me.")

    with caplog.at_level("WARNING"):
        second = crud.create_feedback(db_session, raw_text="Duplicate me.")

    assert second.id is not None
    assert "duplicate" in caplog.text.lower()


def test_get_or_create_theme_deduplicates(db_session):
    first = crud.get_or_create_theme(db_session, "Slow Dashboard")
    second = crud.get_or_create_theme(db_session, "Slow Dashboard")

    assert first.id == second.id


def test_apply_classification_updates_fields(db_session):
    feedback = crud.create_feedback(db_session, raw_text="Cannot log in.")

    updated = crud.apply_classification(
        db_session,
        feedback,
        main_category=MainCategory.INCIDENT,
        sub_category=SubCategory.LOGIN_ISSUE,
        sentiment=Sentiment.NEGATIVE,
        priority=Priority.HIGH,
        confidence=90,
        summary="Customer cannot log in.",
        theme_names=["Login Issue"],
    )

    assert updated.main_category == MainCategory.INCIDENT
    assert updated.sub_category == SubCategory.LOGIN_ISSUE
    assert updated.sentiment == Sentiment.NEGATIVE
    assert updated.priority == Priority.HIGH
    assert updated.confidence == 90
    assert [t.name for t in updated.themes] == ["Login Issue"]


def test_get_feedback_returns_none_for_missing_id(db_session):
    assert crud.get_feedback(db_session, 999_999) is None


def test_list_feedback_filters_by_main_category(db_session):
    incident = crud.create_feedback(db_session, raw_text="App crashed.")
    crud.apply_classification(
        db_session,
        incident,
        main_category=MainCategory.INCIDENT,
        sub_category=SubCategory.APPLICATION_CRASH,
        sentiment=Sentiment.NEGATIVE,
        priority=Priority.HIGH,
        confidence=90,
        summary="Crash report.",
        theme_names=[],
    )

    request = crud.create_feedback(db_session, raw_text="Please add dark mode.")
    crud.apply_classification(
        db_session,
        request,
        main_category=MainCategory.SERVICE_REQUEST,
        sub_category=SubCategory.FEATURE_REQUEST,
        sentiment=Sentiment.NEUTRAL,
        priority=Priority.LOW,
        confidence=90,
        summary="Feature request.",
        theme_names=[],
    )

    results = crud.list_feedback(db_session, main_category=MainCategory.INCIDENT)

    assert len(results) == 1
    assert results[0].id == incident.id


def test_list_feedback_search_matches_case_insensitively(db_session):
    crud.create_feedback(db_session, raw_text="The Dashboard is slow.")
    crud.create_feedback(db_session, raw_text="Unrelated feedback.")

    results = crud.list_feedback(db_session, search="dashboard")

    assert len(results) == 1
    assert "Dashboard" in results[0].raw_text


def test_list_feedback_respects_pagination(db_session):
    for i in range(5):
        crud.create_feedback(db_session, raw_text=f"Feedback {i}")

    page = crud.list_feedback(db_session, skip=2, limit=2)

    assert len(page) == 2
