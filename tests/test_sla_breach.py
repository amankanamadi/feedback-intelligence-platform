from datetime import datetime, timedelta, timezone

from app.database import crud
from app.database.models import Feedback, FeedbackStatus, MainCategory, Priority


def _seed(db_session, **overrides) -> Feedback:
    defaults = dict(
        raw_text="Some complaint.",
        main_category=MainCategory.HOST_COMPLAINT,
        priority=Priority.HIGH,
        status=FeedbackStatus.NEW,
    )
    defaults.update(overrides)
    feedback = Feedback(**defaults)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_flags_overdue_unresolved_item(db_session):
    overdue = _seed(db_session, sla_due_at=datetime.now(timezone.utc) - timedelta(hours=1))

    count = crud.flag_overdue_sla_breaches(db_session)

    assert count == 1
    db_session.refresh(overdue)
    assert overdue.sla_breached is True


def test_does_not_flag_item_not_yet_due(db_session):
    not_due_yet = _seed(db_session, sla_due_at=datetime.now(timezone.utc) + timedelta(hours=1))

    crud.flag_overdue_sla_breaches(db_session)

    db_session.refresh(not_due_yet)
    assert not_due_yet.sla_breached is False


def test_does_not_flag_resolved_item(db_session):
    resolved = _seed(
        db_session,
        sla_due_at=datetime.now(timezone.utc) - timedelta(hours=1),
        status=FeedbackStatus.RESOLVED,
    )

    crud.flag_overdue_sla_breaches(db_session)

    db_session.refresh(resolved)
    assert resolved.sla_breached is False


def test_does_not_flag_closed_item(db_session):
    closed = _seed(
        db_session,
        sla_due_at=datetime.now(timezone.utc) - timedelta(hours=1),
        status=FeedbackStatus.CLOSED,
    )

    crud.flag_overdue_sla_breaches(db_session)

    db_session.refresh(closed)
    assert closed.sla_breached is False


def test_does_not_flag_item_with_no_sla(db_session):
    no_sla = _seed(db_session, sla_due_at=None)

    crud.flag_overdue_sla_breaches(db_session)

    db_session.refresh(no_sla)
    assert no_sla.sla_breached is False


def test_staff_list_feedback_triggers_flagging(admin_client, db_session):
    overdue = _seed(db_session, sla_due_at=datetime.now(timezone.utc) - timedelta(hours=1))

    response = admin_client.get("/feedback")

    assert response.status_code == 200
    db_session.refresh(overdue)
    assert overdue.sla_breached is True
