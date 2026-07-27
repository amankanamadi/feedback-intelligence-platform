"""Seed synthetic feedback into the running app via its real API, so each
item goes through the actual pipeline (embedding, RAG retrieval,
classification, storage) rather than being inserted directly into
Postgres. Run after scripts/generate_synthetic_feedback.py, against a
running server:

    uvicorn app.main:app --reload &
    python scripts/seed_synthetic_feedback.py
    python scripts/seed_synthetic_feedback.py --dataset scripts/synthetic_dataset_batch2.json

Whatever classification gets stored is the model's own genuine judgment on
each text - the same as any real submission, not an externally injected
label.

Every item also gets synthetic submission metadata (source, product,
module, version, region, name, email, user_id) attached, using the same
random-pool approach as the dashboard form - reasonable here since this
whole record is fabricated test data to begin with, unlike backfilling
metadata onto genuinely real historical feedback.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import httpx

DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "synthetic_dataset.json"
BASE_URL = "http://127.0.0.1:8000"

PRODUCTS = ["Invoicing", "Reporting", "Payments", "Onboarding", "Analytics"]
MODULES = ["Uploads", "Checkout", "Dashboard", "Settings", "Notifications"]
VERSIONS = ["1.4.2", "2.0.0", "2.3.1", "3.1.0", "4.0.0-beta"]
REGIONS = ["US-East", "US-West", "EU-West", "APAC", "LATAM"]
FIRST_NAMES = ["Jordan", "Riley", "Sam", "Casey", "Morgan", "Taylor", "Alex", "Jamie"]
LAST_NAMES = ["Lee", "Patel", "Garcia", "Kim", "Nguyen", "Brown", "Smith", "Chen"]


def synthetic_metadata() -> dict:
    first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
    email = f"{first.lower()}.{last.lower()}@example.com"
    return {
        "source": "Web Form",
        "product": random.choice(PRODUCTS),
        "module": random.choice(MODULES),
        "version": random.choice(VERSIONS),
        "region": random.choice(REGIONS),
        "name": f"{first} {last}",
        "email": email,
        "user_id": email.split("@")[0].replace(".", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"No dataset found at {args.dataset}. Run generate_synthetic_feedback.py first.")
        sys.exit(1)

    texts = json.loads(args.dataset.read_text())
    print(f"Seeding {len(texts)} feedback items against {BASE_URL} ...")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        for i, text in enumerate(texts, start=1):
            payload = {"raw_text": text, **synthetic_metadata()}
            response = client.post("/feedback", json=payload)
            response.raise_for_status()
            created = response.json()
            category = created["main_category"] or "unclassified"
            sub_category = created["sub_category"] or "-"
            print(
                f"[{i}/{len(texts)}] id={created['id']} -> {category}/{sub_category} "
                f"(product={created['product']})"
            )

    print("\nDone. Data is stored with real embeddings, ready for RAG retrieval.")


if __name__ == "__main__":
    main()
