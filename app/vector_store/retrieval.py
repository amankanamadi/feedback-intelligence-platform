from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Feedback


def retrieve_similar_feedback(
    db: Session,
    embedding: list[float],
    n_results: int = 3,
    exclude_id: int | None = None,
) -> list[dict]:
    distance = Feedback.embedding.cosine_distance(embedding).label("distance")
    stmt = select(Feedback, distance).where(Feedback.embedding.isnot(None))
    if exclude_id is not None:
        stmt = stmt.where(Feedback.id != exclude_id)
    stmt = stmt.order_by(distance).limit(n_results)

    hits = []
    for feedback, dist in db.execute(stmt).all():
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
