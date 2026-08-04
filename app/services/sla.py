"""SLA due-date computation.

A business rule, not a tunable infra setting - kept as a module-level
constant here rather than in app/core/config.py's Settings, matching
app/services/acknowledgement.py's LOW_CONFIDENCE_THRESHOLD convention.
Only computes the due date; flipping `Feedback.sla_breached` once that
date passes is a later phase's concern (it needs an actual queue/read
path to act on the breach, which doesn't exist yet).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database.models import Priority

SLA_HOURS_BY_PRIORITY: dict[Priority, int] = {
    Priority.CRITICAL: 4,
    Priority.HIGH: 24,
    Priority.MEDIUM: 72,
    Priority.LOW: 168,
}


def compute_sla_due_at(priority: Priority, *, now: Optional[datetime] = None) -> datetime:
    base = now or datetime.now(timezone.utc)
    return base + timedelta(hours=SLA_HOURS_BY_PRIORITY[priority])
