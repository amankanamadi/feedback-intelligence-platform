"""Full demo-data seed for the Airbnb Guest Experience Intelligence
Platform: accounts, properties, bookings, and hundreds of guest
reviews/host complaints/support tickets submitted through the real
API pipeline (embedding, RAG retrieval, classification, routing, SLA).

Replaces the old scripts/seed_synthetic_feedback.py, which predates the
Airbnb transformation - it had no bookings, no host-linked properties,
and only one demo account per role. This script seeds enough volume and
account variety that every role's dashboard (guest, host, ops, trust &
safety, exec) has real data to look at, not just a token example.

Run against a running server, after generating (or reusing the existing)
synthetic text corpus:

    docker compose up -d db app
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --base-url http://127.0.0.1:8000

What this does, in order (each phase is idempotent on its own terms -
see each phase's own skip check - so a second run is safe):
  1. Ensures 5 staff demo accounts (one per staff role) plus 25 guest and
     10 host demo accounts, all created by a direct DB insert (not
     through POST /auth/register - see ensure_accounts' docstring for
     why). Skipped per account if the email already exists.
  2. Seeds ~50 properties across ~18 cities directly via SQLAlchemy
     (there's no write API for properties), distributed 3-8 per host.
     Skipped entirely if any properties already exist.
  3. Seeds bookings for every guest (4-9 each) across random properties,
     spread over the past 100 days (mostly COMPLETED, so there's
     something to review) through 30 days out (a few UPCOMING, a few
     CANCELLED). Skipped entirely if any bookings already exist.
  4. Submits stay reviews, booking-tied complaints, and general
     complaints/support tickets through POST /feedback, exactly as a
     real guest or host would - whatever classification/routing/SLA
     comes out is the model's own judgment on the text, not an
     externally injected label. Skipped entirely if feedback already
     exists (this is the expensive, real-OpenAI-calls phase).
  5. As a Support Manager, responds to a sample of open cases (creates
     the "you have a new response" notification for real); as the
     affected guests, accepts or rejects a sample of those responses
     (rejecting triggers real escalation).
  6. Adds a handful of properties to about half the guests' wishlists.

Env vars (all optional):
  DEMO_PASSWORD  Password used for every demo account. Default: Demo12345!
  API_BASE_URL   Base URL of the running API. Default: http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.security import ACCESS_TOKEN_COOKIE, create_access_token, hash_password  # noqa: E402
from app.database import crud  # noqa: E402
from app.database.models import (  # noqa: E402
    Booking,
    BookingStatus,
    Feedback,
    FeedbackSource,
    Property,
    PropertyType,
    Role,
    User,
)
from app.database.session import SessionLocal  # noqa: E402

DEFAULT_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Demo12345!")
EMAIL_DOMAIN = "airbnb-gx.internal"

# --- 1. Accounts -----------------------------------------------------------

STAFF_DEMO_ACCOUNTS: list[tuple[str, str, Role]] = [
    ("support.manager.demo", "Demo Support Manager", Role.SUPPORT_MANAGER),
    ("ops.manager.demo", "Demo Ops Manager", Role.OPS_MANAGER),
    ("product.manager.demo", "Demo Product Manager", Role.PRODUCT_MANAGER),
    ("trust.safety.demo", "Demo Trust & Safety", Role.TRUST_SAFETY),
    ("exec.demo", "Demo Exec", Role.EXEC),
]

GUEST_FIRST_NAMES = [
    "Ava", "Noah", "Mia", "Liam", "Zoe", "Ethan", "Grace", "Lucas", "Chloe", "Mason",
    "Layla", "Owen", "Nora", "Aiden", "Ivy", "Caleb", "Ruby", "Elias", "Hazel", "Leo",
    "Willow", "Jasper", "Freya", "Theo", "Iris",
]
HOST_FULL_NAMES = [
    "Maria Alvarez", "James Whitfield", "Fiona MacLeod", "Joana Ferreira", "Made Wirawan",
    "Marc Puig", "Thandiwe Mokoena", "Yuki Tanaka", "Camila Reyes", "Aroha Ngata",
]


def guest_accounts() -> list[tuple[str, str, Role]]:
    accounts = [(f"guest.demo@{EMAIL_DOMAIN}", "Demo Guest", Role.GUEST)]
    for i, first_name in enumerate(GUEST_FIRST_NAMES[1:], start=2):
        accounts.append((f"guest{i:02d}.demo@{EMAIL_DOMAIN}", f"{first_name} (Demo Guest)", Role.GUEST))
    return accounts


def host_accounts() -> list[tuple[str, str, Role]]:
    accounts = [(f"host.demo@{EMAIL_DOMAIN}", "Demo Host", Role.HOST)]
    for i, full_name in enumerate(HOST_FULL_NAMES[1:], start=2):
        accounts.append((f"host{i:02d}.demo@{EMAIL_DOMAIN}", full_name, Role.HOST))
    return accounts


def all_accounts() -> list[tuple[str, str, Role]]:
    staff = [(f"{local}@{EMAIL_DOMAIN}", name, role) for local, name, role in STAFF_DEMO_ACCOUNTS]
    return staff + guest_accounts() + host_accounts()


def ensure_accounts(db) -> None:
    """Creates every demo account (guest/host included) with a direct DB
    insert rather than through POST /auth/register. Guest/Host are the
    only self-registerable roles at that endpoint, but it's also
    rate-limited to 3/minute/IP - fine for a real signup flow, fatal for
    provisioning 35 accounts back-to-back from one script. A direct
    insert is exactly what the four staff roles already require (no
    self-service path exists for them at all), so this just applies the
    same approach uniformly instead of splitting on role.
    """
    for email, full_name, role in all_accounts():
        if crud.get_user_by_email(db, email) is not None:
            continue
        crud.create_user(db, email=email, hashed_password=hash_password(DEMO_PASSWORD), full_name=full_name, role=role)
        print(f"  Created {email} ({role.value}).")


# --- 2. Properties -----------------------------------------------------------

# name-template, city, country, property_type - a spread of ~50 listings
# across 18 cities/countries, assigned round-robin-ish across the 10 demo
# hosts below (3-8 properties each) once host accounts exist.
PROPERTY_TEMPLATES: list[tuple[str, str, str, PropertyType]] = [
    ("Sunset Loft — Unit 4B", "Austin", "USA", PropertyType.ENTIRE_HOME),
    ("Riverside Studio", "Austin", "USA", PropertyType.PRIVATE_ROOM),
    ("South Congress Bungalow", "Austin", "USA", PropertyType.ENTIRE_HOME),
    ("The Reading Room Cottage", "Edinburgh", "United Kingdom", PropertyType.ENTIRE_HOME),
    ("Old Town Castle View Flat", "Edinburgh", "United Kingdom", PropertyType.PRIVATE_ROOM),
    ("Leith Harbour Loft", "Edinburgh", "United Kingdom", PropertyType.ENTIRE_HOME),
    ("Alfama Blue Tile Flat", "Lisbon", "Portugal", PropertyType.ENTIRE_HOME),
    ("Bairro Alto Rooftop Suite", "Lisbon", "Portugal", PropertyType.PRIVATE_ROOM),
    ("Belem Riverside Apartment", "Lisbon", "Portugal", PropertyType.ENTIRE_HOME),
    ("Rice Paddy View Bungalow", "Ubud", "Indonesia", PropertyType.ENTIRE_HOME),
    ("Jungle Canopy Treehouse", "Ubud", "Indonesia", PropertyType.ENTIRE_HOME),
    ("Monkey Forest Garden Room", "Ubud", "Indonesia", PropertyType.PRIVATE_ROOM),
    ("Gothic Quarter Hideaway", "Barcelona", "Spain", PropertyType.ENTIRE_HOME),
    ("Sagrada Familia View Room", "Barcelona", "Spain", PropertyType.PRIVATE_ROOM),
    ("Barceloneta Beach Flat", "Barcelona", "Spain", PropertyType.ENTIRE_HOME),
    ("Table Mountain Vista House", "Cape Town", "South Africa", PropertyType.ENTIRE_HOME),
    ("Camps Bay Beach Studio", "Cape Town", "South Africa", PropertyType.ENTIRE_HOME),
    ("Bo-Kaap Colourful Cottage", "Cape Town", "South Africa", PropertyType.PRIVATE_ROOM),
    ("Shibuya Micro Apartment", "Tokyo", "Japan", PropertyType.ENTIRE_HOME),
    ("Asakusa Tatami Room", "Tokyo", "Japan", PropertyType.SHARED_ROOM),
    ("Shimokitazawa Loft", "Tokyo", "Japan", PropertyType.ENTIRE_HOME),
    ("Roma Norte Art Deco Flat", "Mexico City", "Mexico", PropertyType.ENTIRE_HOME),
    ("Condesa Garden House", "Mexico City", "Mexico", PropertyType.ENTIRE_HOME),
    ("Coyoacan Courtyard Suite", "Mexico City", "Mexico", PropertyType.PRIVATE_ROOM),
    ("Ponsonby Villa Guest Suite", "Auckland", "New Zealand", PropertyType.PRIVATE_ROOM),
    ("Waiheke Vineyard Cottage", "Auckland", "New Zealand", PropertyType.ENTIRE_HOME),
    ("Marina Skyline Penthouse", "Dubai", "United Arab Emirates", PropertyType.ENTIRE_HOME),
    ("Desert Palm Villa", "Dubai", "United Arab Emirates", PropertyType.ENTIRE_HOME),
    ("Al Fahidi Heritage Room", "Dubai", "United Arab Emirates", PropertyType.PRIVATE_ROOM),
    ("Palermo Soho Loft", "Buenos Aires", "Argentina", PropertyType.ENTIRE_HOME),
    ("Recoleta Classic Flat", "Buenos Aires", "Argentina", PropertyType.PRIVATE_ROOM),
    ("Northern Lights Cabin", "Reykjavik", "Iceland", PropertyType.ENTIRE_HOME),
    ("Old Harbour Studio", "Reykjavik", "Iceland", PropertyType.ENTIRE_HOME),
    ("Medina Courtyard Riad", "Marrakech", "Morocco", PropertyType.ENTIRE_HOME),
    ("Majorelle Garden View Room", "Marrakech", "Morocco", PropertyType.PRIVATE_ROOM),
    ("Trastevere Cobblestone Flat", "Rome", "Italy", PropertyType.ENTIRE_HOME),
    ("Vatican View Studio", "Rome", "Italy", PropertyType.PRIVATE_ROOM),
    ("Monti Artist Loft", "Rome", "Italy", PropertyType.ENTIRE_HOME),
    ("Le Marais Boutique Flat", "Paris", "France", PropertyType.ENTIRE_HOME),
    ("Montmartre Attic Room", "Paris", "France", PropertyType.PRIVATE_ROOM),
    ("Canal Saint-Martin Loft", "Paris", "France", PropertyType.ENTIRE_HOME),
    ("Gamla Stan Historic Flat", "Stockholm", "Sweden", PropertyType.ENTIRE_HOME),
    ("Sodermalm Design Studio", "Stockholm", "Sweden", PropertyType.ENTIRE_HOME),
    ("Bondi Beach House", "Sydney", "Australia", PropertyType.ENTIRE_HOME),
    ("Surry Hills Terrace Room", "Sydney", "Australia", PropertyType.PRIVATE_ROOM),
    ("Newtown Warehouse Loft", "Sydney", "Australia", PropertyType.ENTIRE_HOME),
    ("Koh Samui Beachfront Villa", "Koh Samui", "Thailand", PropertyType.ENTIRE_HOME),
    ("Chiang Mai Teak House", "Chiang Mai", "Thailand", PropertyType.ENTIRE_HOME),
    ("Old City Riad Suite", "Fes", "Morocco", PropertyType.PRIVATE_ROOM),
    ("Banff Alpine Cabin", "Banff", "Canada", PropertyType.ENTIRE_HOME),
    ("Whistler Ski Chalet Room", "Whistler", "Canada", PropertyType.PRIVATE_ROOM),
]

MIN_PROPERTIES_PER_HOST = 3
MAX_PROPERTIES_PER_HOST = 8


def seed_properties(db, host_ids: list[int], host_names: dict[int, str]) -> list[Property]:
    existing = list(db.scalars(select(Property)))
    if existing:
        print(f"  {len(existing)} properties already exist - skipping property seed.")
        return existing

    sizes = [MIN_PROPERTIES_PER_HOST] * len(host_ids)
    remaining = len(PROPERTY_TEMPLATES) - sum(sizes)
    idx = 0
    while remaining > 0:
        if sizes[idx] < MAX_PROPERTIES_PER_HOST:
            sizes[idx] += 1
            remaining -= 1
        idx = (idx + 1) % len(host_ids)

    templates = list(PROPERTY_TEMPLATES)
    random.shuffle(templates)
    properties: list[Property] = []
    cursor = 0
    for host_id, size in zip(host_ids, sizes):
        for name, city, country, property_type in templates[cursor : cursor + size]:
            properties.append(
                Property(
                    name=name,
                    host_name=host_names[host_id],
                    host_id=host_id,
                    city=city,
                    country=country,
                    property_type=property_type,
                )
            )
        cursor += size

    db.add_all(properties)
    db.commit()
    for property_ in properties:
        db.refresh(property_)
    print(f"  Seeded {len(properties)} properties across {len(host_ids)} hosts.")
    return properties


# --- 3. Bookings -------------------------------------------------------------

MIN_BOOKINGS_PER_GUEST = 4
MAX_BOOKINGS_PER_GUEST = 9


def seed_bookings(db, guest_ids: list[int], property_ids: list[int], today: date) -> list[Booking]:
    existing = list(db.scalars(select(Booking)))
    if existing:
        print(f"  {len(existing)} bookings already exist - skipping booking seed.")
        return existing

    bookings: list[Booking] = []
    for guest_id in guest_ids:
        for n in range(random.randint(MIN_BOOKINGS_PER_GUEST, MAX_BOOKINGS_PER_GUEST)):
            roll = random.random()
            if roll < 0.75:
                status = BookingStatus.COMPLETED
                check_in = today - timedelta(days=random.randint(10, 100))
            elif roll < 0.90:
                status = BookingStatus.UPCOMING
                check_in = today + timedelta(days=random.randint(3, 45))
            else:
                status = BookingStatus.CANCELLED
                check_in = today + timedelta(days=random.randint(-30, 30))
            check_out = check_in + timedelta(days=random.randint(2, 10))
            confirmation_code = f"BK{guest_id:04d}{n:02d}"
            bookings.append(
                Booking(
                    confirmation_code=confirmation_code,
                    guest_id=guest_id,
                    property_id=random.choice(property_ids),
                    check_in_date=check_in,
                    check_out_date=check_out,
                    status=status,
                )
            )

    db.add_all(bookings)
    db.commit()
    for booking in bookings:
        db.refresh(booking)
    completed = sum(1 for b in bookings if b.status == BookingStatus.COMPLETED)
    print(f"  Seeded {len(bookings)} bookings ({completed} completed, ready to review).")
    return bookings


# --- 4. Feedback: reviews + complaints/tickets through the real pipeline ----

REVIEW_RATING_FIELDS = [
    "cleanliness_rating", "housekeeping_rating", "amenities_rating",
    "communication_rating", "checkin_rating", "location_rating", "value_rating",
]


def _load_text_pool() -> list[str]:
    pool: list[str] = []
    for filename in ("synthetic_dataset.json", "synthetic_dataset_batch2.json"):
        path = Path(__file__).resolve().parent / filename
        if path.exists():
            pool.extend(json.loads(path.read_text()))
    random.shuffle(pool)
    return pool


def _random_rating() -> int:
    # Skewed positive (most stays go fine) with a real negative minority -
    # gives the sentiment/rating charts actual variance to show, not a
    # flat wall of 5s.
    return random.choices([1, 2, 3, 4, 5], weights=[5, 8, 15, 32, 40])[0]


def _jittered_rating(overall: int) -> int:
    return max(1, min(5, overall + random.choice([-1, -1, 0, 0, 0, 1])))


def authenticated_client(base_url: str, user: User) -> httpx.Client:
    """Builds a client already carrying a valid access-token cookie,
    minted directly with the same create_access_token the real
    /auth/login route uses - this script already has DB access, and
    logging in via HTTP for ~35 accounts back-to-back would blow through
    /auth/login's 5/minute-per-IP rate limit (all these requests come
    from the same script/IP). No password check needed here since we
    already know the account is a real, just-provisioned demo user.
    """
    client = httpx.Client(base_url=base_url, timeout=60.0)
    token = create_access_token(user, get_settings())
    client.cookies.set(ACCESS_TOKEN_COOKIE, token)
    return client


def _metadata_for(source: FeedbackSource) -> dict:
    metadata: dict = {"source": source.value}
    if random.random() < 0.3:
        metadata["version"] = random.choice(["2.4.0", "2.5.1", "3.0.0", "3.1.2"])
        metadata["device"] = random.choice(["iPhone 14", "Samsung Galaxy S23", "Google Pixel 8", "MacBook Pro"])
        metadata["browser"] = random.choice(["Safari", "Chrome", "Firefox"])
        metadata["platform"] = random.choice(["iOS", "Android", "Web", "macOS"])
    return metadata


def seed_feedback(
    db,
    bookings: list[Booking],
    text_pool: list[str],
    guest_clients: dict[int, httpx.Client],
    host_clients: dict[int, httpx.Client],
) -> None:
    existing_count = db.scalar(select(func.count()).select_from(Feedback))
    if existing_count and existing_count > 0:
        print(f"  {existing_count} feedback rows already exist - skipping feedback seed (the expensive phase).")
        return

    text_iter = iter(text_pool * 3)  # generous repetition budget; we draw far fewer than this
    submitted = 0
    completed_bookings = [b for b in bookings if b.status == BookingStatus.COMPLETED]

    for booking in completed_bookings:
        guest_client = guest_clients[booking.guest_id]

        if random.random() < 0.85:
            # overall_rating is never client-supplied - the backend
            # derives it as the rounded mean of these seven categories.
            overall_seed = _random_rating()
            payload = {
                "raw_text": next(text_iter),
                "booking_id": booking.id,
                **{field: _jittered_rating(overall_seed) for field in REVIEW_RATING_FIELDS},
                **_metadata_for(FeedbackSource.POST_STAY_SURVEY),
            }
            response = guest_client.post("/feedback", json=payload)
            if response.status_code < 400:
                submitted += 1
            else:
                print(f"  Review FAILED for booking {booking.id}: {response.status_code} {response.text[:150]}")

        if random.random() < 0.25:
            property_host_id = db.get(Property, booking.property_id).host_id
            submitter = host_clients.get(property_host_id, guest_client) if random.random() < 0.3 else guest_client
            payload = {
                "raw_text": next(text_iter),
                "booking_id": booking.id,
                **_metadata_for(FeedbackSource.POST_STAY_SURVEY),
            }
            response = submitter.post("/feedback", json=payload)
            if response.status_code < 400:
                submitted += 1
            else:
                print(f"  Booking complaint FAILED for booking {booking.id}: {response.status_code} {response.text[:150]}")

        if submitted % 25 == 0 and submitted > 0:
            print(f"  ... {submitted} feedback items submitted so far")

    # General submissions, not tied to any booking - app issues, feature
    # requests, payments/refunds, and property-scoped complaints - spread
    # across all guest and host accounts so every account has some
    # activity, not just guest.demo/host.demo. A guest can only ever
    # reference a property through one of their own real bookings (the
    # backend rejects a guest-submitted property_id with no booking_id);
    # a host has no "booking" of their own, so they still get the direct
    # property_id tag.
    property_ids = [p.id for p in db.scalars(select(Property))]
    bookings_by_guest: dict[int, list[int]] = {}
    for b in bookings:
        bookings_by_guest.setdefault(b.guest_id, []).append(b.id)

    guest_items = list(guest_clients.items())
    host_items = list(host_clients.items())
    guest_share = len(guest_items) / (len(guest_items) + len(host_items))
    general_target = 90
    for _ in range(general_target):
        if random.random() < guest_share:
            guest_id, client = random.choice(guest_items)
        else:
            guest_id, client = None, random.choice(host_items)[1]

        metadata = _metadata_for(random.choice(list(FeedbackSource)))
        if random.random() < 0.6:
            if guest_id is not None and bookings_by_guest.get(guest_id):
                metadata["booking_id"] = random.choice(bookings_by_guest[guest_id])
            elif guest_id is None and property_ids:
                metadata["property_id"] = random.choice(property_ids)
            # A guest with no bookings at all simply goes untagged this
            # round rather than violating the booking_id requirement.
        payload = {"raw_text": next(text_iter), **metadata}
        response = client.post("/feedback", json=payload)
        if response.status_code < 400:
            submitted += 1
        else:
            print(f"  General submission FAILED: {response.status_code} {response.text[:150]}")

    print(f"  Submitted {submitted} feedback items through the real classification pipeline.")


# --- 5. Staff responses + guest decisions ------------------------------------

def seed_responses_and_decisions(support_client: httpx.Client, guest_clients: dict[int, httpx.Client]) -> None:
    response = support_client.get("/feedback", params={"status": "New", "limit": 60})
    response.raise_for_status()
    items = response.json()
    if not items:
        print("  No open cases to respond to - skipping.")
        return

    sample = items[: min(30, len(items))]
    responded_guest_items: list[dict] = []
    for item in sample:
        resolve_directly = random.random() < 0.4
        payload = {
            "admin_response": "Thanks for flagging this - we've reviewed your case and here's what we're doing about it.",
            "status": "Resolved" if resolve_directly else "In Review",
        }
        patch_response = support_client.patch(f"/feedback/{item['id']}", json=payload)
        if patch_response.status_code >= 400:
            continue
        if not resolve_directly and item.get("user_id") in guest_clients:
            responded_guest_items.append(item)

    decided = 0
    for item in responded_guest_items:
        guest_client = guest_clients[item["user_id"]]
        decision = "Accepted" if random.random() < 0.7 else "Rejected"
        decision_response = guest_client.post(f"/feedback/{item['id']}/decision", json={"decision": decision})
        if decision_response.status_code < 400:
            decided += 1

    print(f"  Responded to {len(sample)} cases; {decided} guests accepted/rejected their resolution.")


# --- 6. Wishlists -------------------------------------------------------------

def seed_wishlists(guest_clients: dict[int, httpx.Client], property_ids: list[int]) -> None:
    added = 0
    for i, (guest_id, client) in enumerate(guest_clients.items()):
        if i % 2 != 0:  # about half the guests
            continue
        for property_id in random.sample(property_ids, k=min(random.randint(2, 5), len(property_ids))):
            response = client.post(f"/wishlist/{property_id}")
            if response.status_code < 400:
                added += 1
    print(f"  Added {added} wishlist entries.")


def print_demo_credentials() -> None:
    print(f"\n=== Demo login credentials (password: {DEMO_PASSWORD} for all) ===")
    for local, _, role in STAFF_DEMO_ACCOUNTS:
        print(f"  {role.value:16s} {local}@{EMAIL_DOMAIN}")
    print(f"  {'GUEST':16s} guest.demo@{EMAIL_DOMAIN}  (+ guest02..guest{len(GUEST_FIRST_NAMES):02d}.demo, same domain)")
    print(f"  {'HOST':16s} host.demo@{EMAIL_DOMAIN}  (+ host02..host{len(HOST_FULL_NAMES):02d}.demo, same domain)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("Provisioning demo accounts ...")
        ensure_accounts(db)

        guest_users = [db.scalar(select(User).where(User.email == email)) for email, _, _ in guest_accounts()]
        host_users = [db.scalar(select(User).where(User.email == email)) for email, _, _ in host_accounts()]
        host_names = {u.id: u.full_name for u in host_users}

        print("\nSeeding properties ...")
        properties = seed_properties(db, [u.id for u in host_users], host_names)
        property_ids = [p.id for p in properties]

        print("\nSeeding bookings ...")
        bookings = seed_bookings(db, [u.id for u in guest_users], property_ids, date.today())

        print("\nAuthenticating every demo account ...")
        guest_clients = {u.id: authenticated_client(args.base_url, u) for u in guest_users}
        host_clients = {u.id: authenticated_client(args.base_url, u) for u in host_users}
        support_user = crud.get_user_by_email(db, f"support.manager.demo@{EMAIL_DOMAIN}")
        support_client = authenticated_client(args.base_url, support_user)

        try:
            print("\nSeeding feedback (reviews + complaints + tickets) through the real pipeline ...")
            text_pool = _load_text_pool()
            seed_feedback(db, bookings, text_pool, guest_clients, host_clients)

            print("\nSeeding staff responses and guest decisions ...")
            seed_responses_and_decisions(support_client, guest_clients)

            print("\nSeeding wishlists ...")
            seed_wishlists(guest_clients, property_ids)
        finally:
            support_client.close()
            for client in guest_clients.values():
                client.close()
            for client in host_clients.values():
                client.close()
    finally:
        db.close()

    print("\nDone. Data is stored with real embeddings, ready for RAG retrieval.")
    print_demo_credentials()


if __name__ == "__main__":
    main()
