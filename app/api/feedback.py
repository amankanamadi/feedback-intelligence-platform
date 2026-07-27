import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.classification import classify_feedback
from app.api.schemas import BulkFeedbackCreate, FeedbackCreate, FeedbackRead
from app.database import crud
from app.database.models import Feedback, MainCategory, Sentiment
from app.database.session import get_db
from app.vector_store.embeddings import get_embedding
from app.vector_store.retrieval import retrieve_similar_feedback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


def _process_feedback_submission(db: Session, payload: FeedbackCreate) -> Feedback:
    """Create + embed + retrieve RAG context + classify a single item.

    Shared by the single-item and bulk endpoints so both go through
    identical logic. Each step degrades independently on failure (a failed
    embedding/classification never blocks storing the raw feedback).
    """
    feedback = crud.create_feedback(
        db,
        raw_text=payload.raw_text,
        user_id=payload.user_id,
        name=payload.name,
        email=payload.email,
        source=payload.source,
        product=payload.product,
        module=payload.module,
        version=payload.version,
        device=payload.device,
        browser=payload.browser,
        platform=payload.platform,
        region=payload.region,
    )

    embedding = None
    similar_examples: list[dict] = []
    try:
        embedding = get_embedding(payload.raw_text)
        similar_examples = retrieve_similar_feedback(db, embedding, n_results=3, exclude_id=feedback.id)
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
        try:
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
        except Exception:
            db.rollback()
            logger.exception("Saving classification failed for feedback %s; leaving unclassified", feedback.id)

    if embedding is not None:
        try:
            crud.set_embedding(db, feedback, embedding)
        except Exception:
            logger.exception("Embedding storage failed for feedback %s", feedback.id)

    return feedback


@router.post("/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackRead:
    return _process_feedback_submission(db, payload)


@router.post("/bulk-upload", response_model=list[FeedbackRead], status_code=status.HTTP_201_CREATED)
def bulk_upload_feedback(payload: BulkFeedbackCreate, db: Session = Depends(get_db)) -> list[FeedbackRead]:
    return [_process_feedback_submission(db, item) for item in payload.items]


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
