from __future__ import annotations

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
