from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    Feedback,
    FeedbackSource,
    MainCategory,
    Priority,
    Sentiment,
    SubCategory,
    Theme,
)

logger = logging.getLogger(__name__)


def get_or_create_theme(db: Session, name: str) -> Theme:
    theme = db.scalar(select(Theme).where(Theme.name == name))
    if theme is None:
        theme = Theme(name=name)
        db.add(theme)
        db.flush()
    return theme


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


def create_feedback(
    db: Session,
    raw_text: str,
    theme_names: list[str] | None = None,
    *,
    user_id: str | None = None,
    name: str | None = None,
    email: str | None = None,
    source: FeedbackSource | None = None,
    product: str | None = None,
    module: str | None = None,
    version: str | None = None,
    device: str | None = None,
    browser: str | None = None,
    platform: str | None = None,
    region: str | None = None,
) -> Feedback:
    existing_id = db.scalar(select(Feedback.id).where(Feedback.raw_text == raw_text).limit(1))
    if existing_id is not None:
        logger.warning(
            "Duplicate feedback submission: identical raw_text already exists as feedback %s",
            existing_id,
        )

    feedback = Feedback(
        raw_text=raw_text,
        user_id=user_id,
        name=name,
        email=email,
        source=source,
        product=product,
        module=module,
        version=version,
        device=device,
        browser=browser,
        platform=platform,
        region=region,
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
) -> Feedback:
    feedback.main_category = main_category
    feedback.sub_category = sub_category
    feedback.sentiment = sentiment
    feedback.priority = priority
    feedback.confidence = confidence
    feedback.summary = summary
    feedback.themes = _resolve_themes(db, theme_names)

    db.commit()
    db.refresh(feedback)
    return feedback


def set_embedding(db: Session, feedback: Feedback, embedding: list[float]) -> Feedback:
    feedback.embedding = embedding
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
) -> list[Feedback]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc())
    if main_category is not None:
        stmt = stmt.where(Feedback.main_category == main_category)
    if sentiment is not None:
        stmt = stmt.where(Feedback.sentiment == sentiment)
    if search:
        stmt = stmt.where(Feedback.raw_text.ilike(f"%{search}%"))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))
