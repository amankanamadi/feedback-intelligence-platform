"""One-time backfill for feedback rows that predate `property_id` (e.g. rows
imported before the Property model existed, or created without a listing
reference). Assigns a random existing Property to any row where
`property_id` is still null, so the table isn't a wall of "no listing" rows.

This is the direct replacement for the old PRODUCTS/MODULES/REGIONS
backfill from the SaaS-support domain - those columns (`product`, `module`,
`region`) no longer exist on Feedback, having been replaced by the
`property_id` FK, so this script no longer touches them.

Only fills `property_id` where it's actually None on a given row; never
overwrites a value that's already set. Skips entirely (with a message) if
no Property rows exist yet - run scripts/seed_synthetic_feedback.py first,
which seeds Property rows before submitting any feedback.

user_id/name/email are deliberately left alone - those describe a real
person and shouldn't be fabricated onto historical entries.

Run against the shared dev database:

    python scripts/backfill_feedback_metadata.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database.models import Feedback, Property
from app.database.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        properties = list(db.scalars(select(Property)))
        if not properties:
            print("No Property rows exist yet - run scripts/seed_synthetic_feedback.py first. Nothing to backfill.")
            return

        rows = db.scalars(select(Feedback).where(Feedback.property_id.is_(None))).all()
        print(f"Found {len(rows)} feedback rows missing a property_id.")

        for row in rows:
            row.property_id = random.choice(properties).id

        db.commit()
        print(f"Backfilled {len(rows)} rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
