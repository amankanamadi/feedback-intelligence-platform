"""Notification message selection for a PATCH /feedback/{id} update.

Deterministic, not an AI call - mirrors app/services/acknowledgement.py's
and app/services/routing.py's pure-function convention. At most one
notification is created per PATCH, prioritized: a resolution matters more
to the submitter than "someone replied" if both happen in the same call.
"""
from __future__ import annotations

from typing import Optional


def build_patch_notification(
    *, status_changed_to_resolved: bool, admin_response_changed: bool
) -> Optional[str]:
    if status_changed_to_resolved:
        return "Your feedback has been marked as resolved."
    if admin_response_changed:
        return "You have a new response to your feedback."
    return None
