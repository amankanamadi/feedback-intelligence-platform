"""One-time backfill for feedback rows created before metadata capture
existed. Fills source/product/module/version/region wherever they're still
null, using the same random pools the dashboard form uses for new
submissions - so the table isn't a wall of "-" placeholders for old rows.

Only fills fields that are actually None on a given row; never overwrites
a value that's already set. user_id/name/email are deliberately left
alone - those describe a real person and shouldn't be fabricated onto
historical entries.

Run against the shared dev database:

    python scripts/backfill_feedback_metadata.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import or_, select

from app.database.models import Feedback, FeedbackSource
from app.database.session import SessionLocal

PRODUCTS = ["Invoicing", "Reporting", "Payments", "Onboarding", "Analytics"]
MODULES = ["Uploads", "Checkout", "Dashboard", "Settings", "Notifications"]
VERSIONS = ["1.4.2", "2.0.0", "2.3.1", "3.1.0", "4.0.0-beta"]
REGIONS = ["US-East", "US-West", "EU-West", "APAC", "LATAM"]


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(Feedback).where(
                or_(
                    Feedback.source.is_(None),
                    Feedback.product.is_(None),
                    Feedback.module.is_(None),
                    Feedback.version.is_(None),
                    Feedback.region.is_(None),
                )
            )
        ).all()
        print(f"Found {len(rows)} feedback rows missing some metadata.")

        for row in rows:
            if row.source is None:
                row.source = FeedbackSource.WEB_FORM
            if row.product is None:
                row.product = random.choice(PRODUCTS)
            if row.module is None:
                row.module = random.choice(MODULES)
            if row.version is None:
                row.version = random.choice(VERSIONS)
            if row.region is None:
                row.region = random.choice(REGIONS)

        db.commit()
        print(f"Backfilled {len(rows)} rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
