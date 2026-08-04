from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import (
    Attachment,
    Booking,
    BookingStatus,
    Feedback,
    FeedbackSource,
    FeedbackStatus,
    MainCategory,
    Notification,
    PasswordResetToken,
    Priority,
    Property,
    Role,
    Sentiment,
    SubCategory,
    Tag,
    Theme,
    User,
    Wishlist,
)

logger = logging.getLogger(__name__)


def get_or_create_theme(db: Session, name: str) -> Theme:
    theme = db.scalar(select(Theme).where(Theme.name == name))
    if theme is None:
        theme = Theme(name=name)
        db.add(theme)
        db.flush()
    return theme


def get_or_create_tag(db: Session, name: str) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.name == name))
    if tag is None:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    return tag


def _dedupe_preserve_order(names: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped = []
    for name in names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped


def _resolve_themes(db: Session, theme_names: list[str]) -> list[Theme]:
    """Resolve theme names to Theme rows, deduplicating first.

    Duplicate names (e.g. an LLM returning ["X", "X"]) would otherwise
    resolve to the same Theme object twice in the collection, and
    SQLAlchemy would try to insert the same (feedback_id, theme_id) pair
    twice into feedback_themes' composite primary key, raising an
    IntegrityError. Deduplicating here protects the invariant regardless
    of which caller supplies the names.
    """
    return [get_or_create_theme(db, name) for name in _dedupe_preserve_order(theme_names)]


def _resolve_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    """Same dedupe rationale as _resolve_themes, for the admin-managed Tag."""
    return [get_or_create_tag(db, name) for name in _dedupe_preserve_order(tag_names)]


def create_feedback(
    db: Session,
    raw_text: str,
    theme_names: list[str] | None = None,
    *,
    owner_user_id: int | None = None,
    submitter_user_id_legacy: str | None = None,
    name: str | None = None,
    email: str | None = None,
    source: FeedbackSource | None = None,
    property_id: int | None = None,
    version: str | None = None,
    device: str | None = None,
    browser: str | None = None,
    platform: str | None = None,
    booking_id: int | None = None,
    overall_rating: int | None = None,
    cleanliness_rating: int | None = None,
    communication_rating: int | None = None,
    checkin_rating: int | None = None,
    location_rating: int | None = None,
    value_rating: int | None = None,
) -> Feedback:
    existing_id = db.scalar(select(Feedback.id).where(Feedback.raw_text == raw_text).limit(1))
    if existing_id is not None:
        logger.warning(
            "Duplicate feedback submission: identical raw_text already exists as feedback %s",
            existing_id,
        )

    feedback = Feedback(
        raw_text=raw_text,
        user_id=owner_user_id,
        submitter_user_id_legacy=submitter_user_id_legacy,
        name=name,
        email=email,
        source=source,
        property_id=property_id,
        version=version,
        device=device,
        browser=browser,
        platform=platform,
        booking_id=booking_id,
        overall_rating=overall_rating,
        cleanliness_rating=cleanliness_rating,
        communication_rating=communication_rating,
        checkin_rating=checkin_rating,
        location_rating=location_rating,
        value_rating=value_rating,
    )
    if theme_names:
        feedback.themes = _resolve_themes(db, theme_names)

    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def apply_classification(
    db: Session,
    feedback: Feedback,
    *,
    main_category: MainCategory,
    sub_category: SubCategory,
    sentiment: Sentiment,
    priority: Priority,
    confidence: int,
    summary: str,
    theme_names: list[str],
    recommended_action: str | None = None,
) -> Feedback:
    feedback.main_category = main_category
    feedback.sub_category = sub_category
    feedback.sentiment = sentiment
    feedback.priority = priority
    feedback.confidence = confidence
    feedback.summary = summary
    feedback.recommended_action = recommended_action
    feedback.themes = _resolve_themes(db, theme_names)

    db.commit()
    db.refresh(feedback)
    return feedback


def set_embedding(db: Session, feedback: Feedback, embedding: list[float]) -> Feedback:
    feedback.embedding = embedding
    db.commit()
    db.refresh(feedback)
    return feedback


def set_acknowledgement(db: Session, feedback: Feedback, acknowledgement: str) -> Feedback:
    feedback.acknowledgement = acknowledgement
    db.commit()
    db.refresh(feedback)
    return feedback


def update_feedback_admin_fields(
    db: Session,
    feedback: Feedback,
    *,
    status: FeedbackStatus | None = None,
    priority: Priority | None = None,
    tag_names: list[str] | None = None,
    internal_notes: str | None = None,
    admin_response: str | None = None,
) -> Feedback:
    if status is not None:
        feedback.status = status
    if priority is not None:
        feedback.priority = priority
    if tag_names is not None:
        feedback.tags = _resolve_tags(db, tag_names)
    if internal_notes is not None:
        feedback.internal_notes = internal_notes
    if admin_response is not None:
        feedback.admin_response = admin_response
        feedback.admin_response_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback(db: Session, feedback_id: int) -> Feedback | None:
    return db.get(Feedback, feedback_id)


def list_feedback(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    main_category: MainCategory | None = None,
    sentiment: Sentiment | None = None,
    search: str | None = None,
    source: FeedbackSource | None = None,
    property_id: int | None = None,
    owner_user_id: int | None = None,
) -> list[Feedback]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc())
    if main_category is not None:
        stmt = stmt.where(Feedback.main_category == main_category)
    if sentiment is not None:
        stmt = stmt.where(Feedback.sentiment == sentiment)
    if search:
        stmt = stmt.where(Feedback.raw_text.ilike(f"%{search}%"))
    if source is not None:
        stmt = stmt.where(Feedback.source == source)
    if property_id is not None:
        stmt = stmt.where(Feedback.property_id == property_id)
    # Scopes a GUEST/HOST caller to their own rows; STAFF callers pass None
    # and see everything. Enforced here (not just in the router) so every
    # call site gets the same ownership guarantee for free.
    if owner_user_id is not None:
        stmt = stmt.where(Feedback.user_id == owner_user_id)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def create_attachment(
    db: Session,
    feedback_id: int,
    *,
    filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str,
) -> Attachment:
    attachment = Attachment(
        feedback_id=feedback_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachment(db: Session, attachment_id: int) -> Attachment | None:
    return db.get(Attachment, attachment_id)


def get_property(db: Session, property_id: int) -> Property | None:
    return db.get(Property, property_id)


def list_properties(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    city: str | None = None,
) -> list[Property]:
    stmt = select(Property).order_by(Property.name)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Property.name.ilike(pattern) | Property.city.ilike(pattern) | Property.country.ilike(pattern)
        )
    if city:
        stmt = stmt.where(Property.city.ilike(f"%{city}%"))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(
    db: Session,
    *,
    email: str,
    hashed_password: str,
    full_name: str | None = None,
    role: Role = Role.GUEST,
) -> User:
    user = User(email=email, hashed_password=hashed_password, full_name=full_name, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_password(db: Session, user: User, hashed_password: str) -> User:
    user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(db: Session, user: User, *, full_name: str | None) -> User:
    user.full_name = full_name
    db.commit()
    db.refresh(user)
    return user


def create_password_reset_token(
    db: Session, *, user_id: int, token_hash: str, expires_at: datetime
) -> PasswordResetToken:
    reset_token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def get_valid_reset_token(db: Session, token_hash: str) -> PasswordResetToken | None:
    token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if token is None or token.used_at is not None:
        return None
    if token.expires_at < datetime.now(timezone.utc):
        return None
    return token


def mark_reset_token_used(db: Session, token: PasswordResetToken) -> None:
    token.used_at = datetime.now(timezone.utc)
    db.commit()


def create_booking(
    db: Session,
    *,
    confirmation_code: str,
    guest_id: int,
    property_id: int,
    check_in_date,
    check_out_date,
    status: BookingStatus = BookingStatus.UPCOMING,
) -> Booking:
    booking = Booking(
        confirmation_code=confirmation_code,
        guest_id=guest_id,
        property_id=property_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        status=status,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking_by_confirmation_code(db: Session, confirmation_code: str) -> Booking | None:
    return db.scalar(select(Booking).where(Booking.confirmation_code == confirmation_code))


def get_booking(db: Session, booking_id: int) -> Booking | None:
    return db.get(Booking, booking_id)


def create_notification(
    db: Session, *, user_id: int, message: str, link: str | None = None
) -> Notification:
    notification = Notification(user_id=user_id, message=message, link=link)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications_for_user(
    db: Session, user_id: int, *, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def add_to_wishlist(db: Session, *, guest_id: int, property_id: int) -> Wishlist:
    existing = db.scalar(
        select(Wishlist).where(Wishlist.guest_id == guest_id, Wishlist.property_id == property_id)
    )
    if existing is not None:
        return existing
    wishlist_item = Wishlist(guest_id=guest_id, property_id=property_id)
    db.add(wishlist_item)
    db.commit()
    db.refresh(wishlist_item)
    return wishlist_item


def remove_from_wishlist(db: Session, *, guest_id: int, property_id: int) -> None:
    existing = db.scalar(
        select(Wishlist).where(Wishlist.guest_id == guest_id, Wishlist.property_id == property_id)
    )
    if existing is not None:
        db.delete(existing)
        db.commit()


def list_wishlist_for_guest(db: Session, guest_id: int) -> list[Wishlist]:
    stmt = select(Wishlist).where(Wishlist.guest_id == guest_id).order_by(Wishlist.created_at.desc())
    return list(db.scalars(stmt))


def get_property_average_ratings(db: Session, property_ids: list[int]) -> dict[int, float]:
    """Average `overall_rating` per property, computed only from
    guest-submitted stay reviews (rows where overall_rating is set) - the
    AI classification pipeline never writes to that column, so this can
    never be influenced by anything but real guest input.
    """
    if not property_ids:
        return {}
    stmt = (
        select(Feedback.property_id, func.avg(Feedback.overall_rating))
        .where(Feedback.property_id.in_(property_ids), Feedback.overall_rating.is_not(None))
        .group_by(Feedback.property_id)
    )
    return {property_id: round(float(avg), 1) for property_id, avg in db.execute(stmt).all()}


def has_review_for_booking(db: Session, booking_id: int) -> bool:
    """Whether a stay review has already been submitted for this booking -
    enforces one review per completed stay."""
    existing_id = db.scalar(
        select(Feedback.id)
        .where(Feedback.booking_id == booking_id, Feedback.overall_rating.is_not(None))
        .limit(1)
    )
    return existing_id is not None
