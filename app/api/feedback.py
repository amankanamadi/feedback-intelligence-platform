import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.classification import classify_feedback
from app.api.schemas import FeedbackCreate, FeedbackRead
from app.database import crud
from app.database.models import MainCategory, Sentiment
from app.database.session import get_db
from app.vector_store.embeddings import get_embedding, store_feedback_embedding
from app.vector_store.retrieval import retrieve_similar_feedback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackRead:
    feedback = crud.create_feedback(db, raw_text=payload.raw_text)

    embedding = None
    similar_examples: list[dict] = []
    try:
        embedding = get_embedding(payload.raw_text)
        similar_examples = retrieve_similar_feedback(embedding, n_results=3)
    except Exception:
        logger.exception(
            "Embedding/retrieval failed for feedback %s; classifying without RAG context",
            feedback.id,
        )

    try:
        classification = classify_feedback(payload.raw_text, similar_examples=similar_examples)
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

    if embedding is not None:
        try:
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
            store_feedback_embedding(feedback.id, payload.raw_text, metadata=metadata, embedding=embedding)
        except Exception:
            logger.exception("Embedding storage failed for feedback %s", feedback.id)

    return feedback


@router.get("/feedback", response_model=list[FeedbackRead])
def list_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    main_category: Optional[MainCategory] = Query(None),
    sentiment: Optional[Sentiment] = Query(None),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    db: Session = Depends(get_db),
) -> list[FeedbackRead]:
    return crud.list_feedback(
        db,
        skip=skip,
        limit=limit,
        main_category=main_category,
        sentiment=sentiment,
        search=search,
    )


@router.get("/feedback/{feedback_id}", response_model=FeedbackRead)
def get_feedback(feedback_id: int, db: Session = Depends(get_db)) -> FeedbackRead:
    feedback = crud.get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return feedback
