from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Feedback, MainCategory, Priority, Sentiment, SubCategory, Theme


def get_or_create_theme(db: Session, name: str) -> Theme:
    theme = db.scalar(select(Theme).where(Theme.name == name))
    if theme is None:
        theme = Theme(name=name)
        db.add(theme)
        db.flush()
    return theme


def create_feedback(db: Session, raw_text: str, theme_names: list[str] | None = None) -> Feedback:
    feedback = Feedback(raw_text=raw_text)
    if theme_names:
        feedback.themes = [get_or_create_theme(db, name) for name in theme_names]

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
    feedback.themes = [get_or_create_theme(db, name) for name in theme_names]

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
