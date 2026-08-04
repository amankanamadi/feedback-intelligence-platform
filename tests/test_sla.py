from datetime import datetime, timedelta, timezone

import pytest

from app.database.models import Priority
from app.services.sla import SLA_HOURS_BY_PRIORITY, compute_sla_due_at


@pytest.mark.parametrize("priority,expected_hours", list(SLA_HOURS_BY_PRIORITY.items()))
def test_compute_sla_due_at_uses_the_correct_window(priority, expected_hours):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    due_at = compute_sla_due_at(priority, now=now)

    assert due_at == now + timedelta(hours=expected_hours)


def test_critical_sla_window_is_shorter_than_low():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    critical_due = compute_sla_due_at(Priority.CRITICAL, now=now)
    low_due = compute_sla_due_at(Priority.LOW, now=now)

    assert critical_due < low_due
