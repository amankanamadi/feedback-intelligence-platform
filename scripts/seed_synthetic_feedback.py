"""Seed synthetic Airbnb guest/host feedback into the running app via its
real API, so each item goes through the actual pipeline (embedding, RAG
retrieval, classification, storage) rather than being inserted directly
into Postgres. Run after scripts/generate_synthetic_feedback.py, against a
running server:

    uvicorn app.main:app --reload &
    python scripts/seed_synthetic_feedback.py
    python scripts/seed_synthetic_feedback.py --dataset scripts/synthetic_dataset_batch2.json --base-url http://127.0.0.1:8000

Unlike the old version of this script, there is no admin bootstrap problem
to work around: this script provisions its own demo accounts (one per
Role) the first time it runs, then authenticates as the GUEST/HOST demo
accounts to submit feedback through the real, any-authenticated-user
POST /feedback endpoint - exactly the path a real guest or host would
take. Whatever classification ends up stored is the model's own genuine
judgment on each text, the same as any real submission, not an externally
injected label.

What this script does, in order:
  1. Seed ~24 Property rows directly via SQLAlchemy (there's no write API
     for properties - they're static reference data). Skipped if any
     properties already exist, so this is idempotent.
  2. Ensure one demo User per Role exists. GUEST/HOST are created through
     the real POST /auth/register endpoint (the only roles it will accept
     for self-registration); the four staff roles are provisioned by
     inserting User rows directly, since there is no self-service path to
     staff roles by design. Skipped per-account if the email already
     exists, so this is idempotent too.
  3. Log in as the GUEST and HOST demo accounts and POST each item in the
     dataset to /feedback, alternating between the two, with randomized
     but plausible source/property_id/device metadata attached.
  4. Print all 6 demo credentials so they can be copied into a README.

Env vars (all optional):
  DEMO_PASSWORD  Password used for all 6 demo accounts. Default: Demo12345!
  API_BASE_URL   Base URL of the running API. Default: http://127.0.0.1:8000

Also relies on whatever DATABASE_URL the app itself is configured with
(via app.core.config / .env) for the direct-DB steps (1) and (2) above -
this script must run somewhere that can reach the same Postgres instance
the API server uses.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import crud  # noqa: E402
from app.database.models import FeedbackSource, Property, PropertyType, Role  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402

DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "synthetic_dataset.json"
DEFAULT_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Demo12345!")

# email, full_name, role - GUEST/HOST are self-registerable; the rest are
# provisioned by direct DB insert since staff roles are never
# self-registered.
DEMO_ACCOUNTS: list[tuple[str, str, Role]] = [
    ("guest.demo@airbnb-gx.internal", "Demo Guest", Role.GUEST),
    ("host.demo@airbnb-gx.internal", "Demo Host", Role.HOST),
    ("support.manager.demo@airbnb-gx.internal", "Demo Support Manager", Role.SUPPORT_MANAGER),
    ("ops.manager.demo@airbnb-gx.internal", "Demo Ops Manager", Role.OPS_MANAGER),
    ("product.manager.demo@airbnb-gx.internal", "Demo Product Manager", Role.PRODUCT_MANAGER),
    ("exec.demo@airbnb-gx.internal", "Demo Exec", Role.EXEC),
]
GUEST_DEMO_EMAIL = DEMO_ACCOUNTS[0][0]
HOST_DEMO_EMAIL = DEMO_ACCOUNTS[1][0]
SELF_REGISTERABLE_ROLES = frozenset({Role.GUEST, Role.HOST})

# name, host_name, city, country, property_type - a static, plausible
# spread of ~24 listings across 12 cities/countries. Seeded once; there is
# no create/update/delete API for Property by design.
PROPERTIES: list[tuple[str, str, str, str, PropertyType]] = [
    ("Sunset Loft — Unit 4B", "Maria Alvarez", "Austin", "USA", PropertyType.ENTIRE_HOME),
    ("Riverside Studio Austin", "Maria Alvarez", "Austin", "USA", PropertyType.PRIVATE_ROOM),
    ("The Reading Room Cottage", "James Whitfield", "Edinburgh", "United Kingdom", PropertyType.ENTIRE_HOME),
    ("Old Town Castle View Flat", "Fiona MacLeod", "Edinburgh", "United Kingdom", PropertyType.PRIVATE_ROOM),
    ("Alfama Blue Tile Flat", "Joana Ferreira", "Lisbon", "Portugal", PropertyType.ENTIRE_HOME),
    ("Bairro Alto Rooftop Suite", "Tiago Santos", "Lisbon", "Portugal", PropertyType.PRIVATE_ROOM),
    ("Rice Paddy View Bungalow", "Made Wirawan", "Ubud", "Indonesia", PropertyType.ENTIRE_HOME),
    ("Jungle Canopy Treehouse", "Kadek Sari", "Ubud", "Indonesia", PropertyType.ENTIRE_HOME),
    ("Gothic Quarter Hideaway", "Marc Puig", "Barcelona", "Spain", PropertyType.ENTIRE_HOME),
    ("Sagrada Familia View Room", "Nuria Vidal", "Barcelona", "Spain", PropertyType.PRIVATE_ROOM),
    ("Table Mountain Vista House", "Thandiwe Mokoena", "Cape Town", "South Africa", PropertyType.ENTIRE_HOME),
    ("Camps Bay Beach Studio", "Sipho Dlamini", "Cape Town", "South Africa", PropertyType.ENTIRE_HOME),
    ("Shibuya Micro Apartment", "Yuki Tanaka", "Tokyo", "Japan", PropertyType.ENTIRE_HOME),
    ("Asakusa Tatami Room", "Hiroshi Sato", "Tokyo", "Japan", PropertyType.SHARED_ROOM),
    ("Roma Norte Art Deco Flat", "Camila Reyes", "Mexico City", "Mexico", PropertyType.ENTIRE_HOME),
    ("Condesa Garden House", "Diego Morales", "Mexico City", "Mexico", PropertyType.ENTIRE_HOME),
    ("Ponsonby Villa Guest Suite", "Aroha Ngata", "Auckland", "New Zealand", PropertyType.PRIVATE_ROOM),
    ("Waiheke Vineyard Cottage", "Liam O'Connor", "Auckland", "New Zealand", PropertyType.ENTIRE_HOME),
    ("Marina Skyline Penthouse", "Fatima Al-Rashid", "Dubai", "United Arab Emirates", PropertyType.ENTIRE_HOME),
    ("Desert Palm Villa", "Omar Haddad", "Dubai", "United Arab Emirates", PropertyType.ENTIRE_HOME),
    ("Palermo Soho Loft", "Lucia Fernandez", "Buenos Aires", "Argentina", PropertyType.ENTIRE_HOME),
    ("Recoleta Classic Flat", "Martin Gomez", "Buenos Aires", "Argentina", PropertyType.PRIVATE_ROOM),
    ("Northern Lights Cabin", "Björn Sigurdsson", "Reykjavik", "Iceland", PropertyType.ENTIRE_HOME),
    ("Medina Courtyard Riad", "Amina El Fassi", "Marrakech", "Morocco", PropertyType.ENTIRE_HOME),
]

# Still relevant for App Issues-flavored submissions.
VERSIONS = ["2.4.0", "2.5.1", "3.0.0", "3.1.2", "3.2.0-beta"]
DEVICES = [
    "iPhone 14",
    "iPhone 13",
    "Samsung Galaxy S23",
    "Google Pixel 8",
    "iPad Air",
    "MacBook Pro",
    "Samsung Galaxy A54",
    "Desktop PC",
]
BROWSERS = ["Safari", "Chrome", "Firefox", "Edge", "Samsung Internet"]
PLATFORMS = ["iOS", "Android", "Web", "macOS", "Windows"]


def seed_properties(db) -> list[Property]:
    existing = list(db.scalars(select(Property)))
    if existing:
        print(f"  {len(existing)} properties already exist - skipping property seed.")
        return existing

    properties = [
        Property(name=name, host_name=host_name, city=city, country=country, property_type=property_type)
        for name, host_name, city, country, property_type in PROPERTIES
    ]
    db.add_all(properties)
    db.commit()
    for property_ in properties:
        db.refresh(property_)
    print(f"  Seeded {len(properties)} properties.")
    return properties


def ensure_demo_accounts(db, client: httpx.Client) -> None:
    for email, full_name, role in DEMO_ACCOUNTS:
        if crud.get_user_by_email(db, email) is not None:
            print(f"  {email} already exists - skipping.")
            continue

        if role in SELF_REGISTERABLE_ROLES:
            response = client.post(
                "/auth/register",
                json={"email": email, "password": DEMO_PASSWORD, "full_name": full_name, "role": role.value},
            )
            if response.status_code >= 400:
                print(f"  FAILED to register {email}: {response.status_code} {response.text[:200]}")
                continue
            print(f"  Registered {email} ({role.value}) via /auth/register.")
        else:
            crud.create_user(db, email=email, hashed_password=hash_password(DEMO_PASSWORD), full_name=full_name, role=role)
            print(f"  Created {email} ({role.value}) directly in the database (staff roles aren't self-registered).")


def login_client(base_url: str, email: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=base_url, timeout=30.0)
    response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return client


def synthetic_metadata(property_ids: list[int]) -> dict:
    metadata: dict = {"source": random.choice(list(FeedbackSource)).value}
    # Most items reference a listing; a handful (general app bugs, feature
    # requests) plausibly don't.
    if property_ids and random.random() < 0.8:
        metadata["property_id"] = random.choice(property_ids)
    # Only relevant for a subset of submissions (app/device-flavored
    # issues), so only attach it sometimes.
    if random.random() < 0.35:
        metadata["version"] = random.choice(VERSIONS)
        metadata["device"] = random.choice(DEVICES)
        metadata["browser"] = random.choice(BROWSERS)
        metadata["platform"] = random.choice(PLATFORMS)
    return metadata


def print_demo_credentials() -> None:
    print("\n=== Demo login credentials (same password for all 6) ===")
    for email, _, role in DEMO_ACCOUNTS:
        print(f"  {role.value:16s} {email}")
    print(f"  password: {DEMO_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--count", type=int, default=None, help="Limit how many dataset items to submit.")
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"No dataset found at {args.dataset}. Run generate_synthetic_feedback.py first.")
        sys.exit(1)

    texts = json.loads(args.dataset.read_text())
    if args.count is not None:
        texts = texts[: args.count]

    print("Seeding properties ...")
    db = SessionLocal()
    try:
        properties = seed_properties(db)
        # Extracted while the session is still open - `properties` itself
        # gets expired (and later detached) by the commits inside
        # ensure_demo_accounts below, since SQLAlchemy's default
        # expire_on_commit applies session-wide, not just to rows touched
        # by that particular commit.
        property_ids = [p.id for p in properties]

        print(f"\nProvisioning demo accounts against {args.base_url} ...")
        with httpx.Client(base_url=args.base_url, timeout=30.0) as bootstrap_client:
            ensure_demo_accounts(db, bootstrap_client)
    finally:
        db.close()

    print(f"\nSeeding {len(texts)} feedback items against {args.base_url} as guest.demo/host.demo ...")
    guest_client = login_client(args.base_url, GUEST_DEMO_EMAIL, DEMO_PASSWORD)
    host_client = login_client(args.base_url, HOST_DEMO_EMAIL, DEMO_PASSWORD)
    submitter_clients = [guest_client, host_client]

    try:
        for i, text in enumerate(texts, start=1):
            client = random.choice(submitter_clients)
            payload = {"raw_text": text, **synthetic_metadata(property_ids)}
            try:
                response = client.post("/feedback", json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                print(f"[{i}/{len(texts)}] FAILED: {exc.response.status_code} {exc.response.text[:200]}")
                continue

            created = response.json()
            ack_preview = (created.get("acknowledgement") or "")[:60]
            print(f"[{i}/{len(texts)}] id={created['id']} status={created['status']} ack=\"{ack_preview}\"")
    finally:
        guest_client.close()
        host_client.close()

    print("\nDone. Data is stored with real embeddings, ready for RAG retrieval.")
    print_demo_credentials()


if __name__ == "__main__":
    main()
