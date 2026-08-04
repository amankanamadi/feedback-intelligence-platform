from app.database.models import Feedback, FeedbackStatus, MainCategory, Priority, ResponsibleTeam


def _seed(db_session, **overrides) -> Feedback:
    defaults = dict(
        raw_text="Some complaint.",
        main_category=MainCategory.HOST_COMPLAINT,
        priority=Priority.MEDIUM,
        status=FeedbackStatus.NEW,
    )
    defaults.update(overrides)
    feedback = Feedback(**defaults)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_filter_by_priority(admin_client, db_session):
    critical = _seed(db_session, priority=Priority.CRITICAL)
    _seed(db_session, priority=Priority.LOW)

    response = admin_client.get("/feedback", params={"priority": "Critical"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [critical.id]


def test_filter_by_status(admin_client, db_session):
    resolved = _seed(db_session, status=FeedbackStatus.RESOLVED)
    _seed(db_session, status=FeedbackStatus.NEW)

    response = admin_client.get("/feedback", params={"status": "Resolved"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [resolved.id]


def test_filter_by_responsible_team(admin_client, db_session):
    safety = _seed(db_session, responsible_team=ResponsibleTeam.TRUST_AND_SAFETY)
    _seed(db_session, responsible_team=ResponsibleTeam.HOST)

    response = admin_client.get("/feedback", params={"responsible_team": "Trust & Safety"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [safety.id]


def test_filter_by_escalated(admin_client, db_session):
    escalated = _seed(db_session, escalated=True)
    _seed(db_session, escalated=False)

    response = admin_client.get("/feedback", params={"escalated": "true"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [escalated.id]


def test_filter_by_sla_breached(admin_client, db_session):
    breached = _seed(db_session, sla_breached=True)
    _seed(db_session, sla_breached=False)

    response = admin_client.get("/feedback", params={"sla_breached": "true"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [breached.id]


def test_filter_unresolved(admin_client, db_session):
    unresolved = _seed(db_session, status=FeedbackStatus.IN_PROGRESS)
    _seed(db_session, status=FeedbackStatus.RESOLVED)
    _seed(db_session, status=FeedbackStatus.CLOSED)

    response = admin_client.get("/feedback", params={"unresolved": "true"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [unresolved.id]


def test_filter_has_duplicates(admin_client, db_session):
    original = _seed(db_session)
    _seed(db_session, duplicate_of_feedback_id=original.id)
    _seed(db_session)  # unrelated, no duplicate link either way

    response = admin_client.get("/feedback", params={"has_duplicates": "true"})

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert ids == [original.id]
