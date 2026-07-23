"""Seed synthetic feedback into the running app via its real API, so each
item goes through the actual pipeline (embedding, RAG retrieval,
classification, storage) rather than being inserted directly into
Postgres. Run after scripts/generate_synthetic_feedback.py, against a
running server:

    uvicorn app.main:app --reload &
    python scripts/seed_synthetic_feedback.py

Whatever classification gets stored is the model's own genuine judgment on
each text - the same as any real submission, not an externally injected
label.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

DATASET_PATH = Path(__file__).resolve().parent / "synthetic_dataset.json"
BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    if not DATASET_PATH.exists():
        print(f"No dataset found at {DATASET_PATH}. Run generate_synthetic_feedback.py first.")
        sys.exit(1)

    texts = json.loads(DATASET_PATH.read_text())
    print(f"Seeding {len(texts)} feedback items against {BASE_URL} ...")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        for i, text in enumerate(texts, start=1):
            response = client.post("/feedback", json={"raw_text": text})
            response.raise_for_status()
            created = response.json()
            category = created["main_category"] or "unclassified"
            sub_category = created["sub_category"] or "-"
            print(f"[{i}/{len(texts)}] id={created['id']} -> {category}/{sub_category}")

    print("\nDone. Data is stored with real embeddings, ready for RAG retrieval.")


if __name__ == "__main__":
    main()
