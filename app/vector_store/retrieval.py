from __future__ import annotations

from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Feedback


def retrieve_similar_feedback(
    db: Session,
    embedding: list[float],
    n_results: int = 3,
    exclude_id: int | None = None,
    max_distance: float | None = None,
) -> list[dict]:
    settings = get_settings()
    if max_distance is None:
        max_distance = settings.rag_max_distance

    # Scoped to this transaction only (SET LOCAL resets automatically once
    # the transaction ends) - guards against a hung/blocked query without
    # affecting the statement timeout of any other query on this session.
    db.execute(text(f"SET LOCAL statement_timeout = {int(settings.rag_query_timeout_ms)}"))

    distance_expr = Feedback.embedding.cosine_distance(embedding)
    stmt = (
        select(Feedback, distance_expr.label("distance"))
        .where(Feedback.embedding.isnot(None))
        .where(distance_expr < max_distance)
    )
    if exclude_id is not None:
        stmt = stmt.where(Feedback.id != exclude_id)
    stmt = stmt.order_by(distance_expr).limit(n_results)

    hits = []
    seen_texts: set[str] = set()
    for feedback, dist in db.execute(stmt).all():
        if feedback.raw_text in seen_texts:
            continue
        seen_texts.add(feedback.raw_text)

        metadata = {
            key: value.value
            for key, value in (
                ("main_category", feedback.main_category),
                ("sub_category", feedback.sub_category),
                ("sentiment", feedback.sentiment),
                ("priority", feedback.priority),
            )
            if value is not None
        }
        hits.append({"text": feedback.raw_text, "metadata": metadata, "distance": float(dist)})
    return hits


def find_duplicate_complaint(
    db: Session, embedding: list[float], *, property_id: int, exclude_id: int
) -> Optional[dict]:
    """Whether a near-identical complaint already exists for this property.

    Uses a much tighter distance threshold than retrieve_similar_feedback
    (that one answers "what's loosely related, for RAG context"; this one
    answers "is this the same complaint someone already filed"), and is
    scoped to the same property - a "duplicate" only makes sense within
    the same listing.
    """
    settings = get_settings()
    db.execute(text(f"SET LOCAL statement_timeout = {int(settings.rag_query_timeout_ms)}"))

    distance_expr = Feedback.embedding.cosine_distance(embedding)
    stmt = (
        select(Feedback.id, distance_expr.label("distance"))
        .where(Feedback.embedding.isnot(None))
        .where(Feedback.property_id == property_id)
        .where(Feedback.id != exclude_id)
        .where(distance_expr < settings.duplicate_detection_max_distance)
        .order_by(distance_expr)
        .limit(1)
    )
    row = db.execute(stmt).first()
    if row is None:
        return None
    return {"id": row.id, "distance": float(row.distance)}
