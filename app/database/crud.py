from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Feedback, Theme


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


def get_feedback(db: Session, feedback_id: int) -> Feedback | None:
    return db.get(Feedback, feedback_id)


def list_feedback(db: Session, skip: int = 0, limit: int = 100) -> list[Feedback]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))
