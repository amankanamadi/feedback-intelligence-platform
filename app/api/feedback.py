import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.classification import classify_feedback
from app.api.schemas import FeedbackCreate, FeedbackRead
from app.database import crud
from app.database.session import get_db
from app.vector_store.embeddings import store_feedback_embedding

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackRead:
    feedback = crud.create_feedback(db, raw_text=payload.raw_text)

    try:
        classification = classify_feedback(payload.raw_text)
    except Exception:
        logger.exception("AI classification failed for feedback %s; leaving unclassified", feedback.id)
    else:
        feedback = crud.apply_classification(
            db,
            feedback,
            main_category=classification.main_category,
            sub_category=classification.sub_category,
            sentiment=classification.sentiment,
            priority=classification.priority,
            confidence=classification.confidence,
            summary=classification.summary,
            theme_names=classification.themes,
        )

    try:
        metadata = {"main_category": feedback.main_category.value} if feedback.main_category else {}
        store_feedback_embedding(feedback.id, payload.raw_text, metadata=metadata)
    except Exception:
        logger.exception("Embedding storage failed for feedback %s", feedback.id)

    return feedback


@router.get("/feedback", response_model=list[FeedbackRead])
def list_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[FeedbackRead]:
    return crud.list_feedback(db, skip=skip, limit=limit)


@router.get("/feedback/{feedback_id}", response_model=FeedbackRead)
def get_feedback(feedback_id: int, db: Session = Depends(get_db)) -> FeedbackRead:
    feedback = crud.get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return feedback
