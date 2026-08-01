import logging
from typing import Optional, Union

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.classification import classify_feedback
from app.api.bulk_upload_parsing import parse_bulk_upload_file
from app.api.schemas import (
    BulkFeedbackCreate,
    FeedbackAdminUpdate,
    FeedbackCreate,
    FeedbackStaffRead,
    FeedbackSubmitterRead,
)
from app.core.config import get_settings
from app.core.security import RequireManager, STAFF_ROLES, assert_owns_or_staff, get_current_user
from app.database import crud
from app.database.models import Feedback, FeedbackSource, MainCategory, Sentiment, User
from app.database.session import get_db
from app.services.acknowledgement import generate_acknowledgement
from app.vector_store.embeddings import get_embedding
from app.vector_store.retrieval import retrieve_similar_feedback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


def _shape_feedback(feedback: Feedback, current_user: User) -> Union[FeedbackStaffRead, FeedbackSubmitterRead]:
    """Every feedback-returning route picks the response shape by role and
    constructs the Pydantic model explicitly here, rather than relying on
    a single static response_model - this is what guarantees AI-analysis
    fields are structurally absent from a non-staff response, not merely
    hidden. Routes that call this pass response_model=None so FastAPI
    doesn't re-validate/coerce the result against an inferred schema
    (FeedbackStaffRead being a subclass of FeedbackSubmitterRead makes that
    inference unreliable - it could silently upcast a submitter-shaped
    result).
    """
    if current_user.role in STAFF_ROLES:
        shaped = FeedbackStaffRead.model_validate(feedback)
    else:
        shaped = FeedbackSubmitterRead.model_validate(feedback)
    # property_name/property_city aren't direct Feedback attributes, so
    # from_attributes can't pick them up - fill them in from the loaded
    # relationship here instead.
    shaped.property_name = feedback.property.name if feedback.property else None
    shaped.property_city = feedback.property.city if feedback.property else None
    return shaped


def _validate_property_id(db: Session, property_id: Optional[int]) -> None:
    if property_id is not None and crud.get_property(db, property_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Property {property_id} not found")


def _process_feedback_submission(db: Session, payload: FeedbackCreate, *, owner_user_id: Optional[int]) -> Feedback:
    """Create + embed + retrieve RAG context + classify + acknowledge a
    single item. Shared by the single-item and bulk endpoints so both go
    through identical logic. Each AI step degrades independently on
    failure (a failed embedding/classification never blocks storing the
    raw feedback); the acknowledgement step never fails since it's a pure
    template lookup, not a network call.
    """
    _validate_property_id(db, payload.property_id)

    feedback = crud.create_feedback(
        db,
        raw_text=payload.raw_text,
        owner_user_id=owner_user_id,
        submitter_user_id_legacy=payload.submitter_user_id_legacy,
        name=payload.name,
        email=payload.email,
        source=payload.source,
        property_id=payload.property_id,
        version=payload.version,
        device=payload.device,
        browser=payload.browser,
        platform=payload.platform,
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

    classification = None
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
                recommended_action=classification.recommended_action,
            )
        except Exception:
            db.rollback()
            logger.exception("Saving classification failed for feedback %s; leaving unclassified", feedback.id)
            classification = None

    acknowledgement = generate_acknowledgement(
        sub_category=classification.sub_category if classification else None,
        priority=classification.priority if classification else None,
        confidence=classification.confidence if classification else None,
    )
    feedback = crud.set_acknowledgement(db, feedback, acknowledgement)

    if embedding is not None:
        try:
            crud.set_embedding(db, feedback, embedding)
        except Exception:
            logger.exception("Embedding storage failed for feedback %s", feedback.id)

    return feedback


@router.post("/feedback", response_model=None, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[FeedbackStaffRead, FeedbackSubmitterRead]:
    feedback = _process_feedback_submission(db, payload, owner_user_id=current_user.id)
    return _shape_feedback(feedback, current_user)


@router.post("/bulk-upload", response_model=list[FeedbackStaffRead], status_code=status.HTTP_201_CREATED)
def bulk_upload_feedback(
    payload: BulkFeedbackCreate,
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_db),
) -> list[FeedbackStaffRead]:
    # Staff-imported items (historical/external data) have no real
    # authenticated submitter - left owner_user_id=None, which makes them
    # visible only to staff (a NULL owner never matches a GUEST/HOST's
    # ownership check).
    return [
        _shape_feedback(_process_feedback_submission(db, item, owner_user_id=None), current_user)
        for item in payload.items
    ]


@router.post("/bulk-upload/file", response_model=list[FeedbackStaffRead], status_code=status.HTTP_201_CREATED)
async def bulk_upload_feedback_file(
    file: UploadFile = File(...),
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_db),
) -> list[FeedbackStaffRead]:
    settings = get_settings()
    raw_bytes = await file.read()
    if len(raw_bytes) > settings.bulk_upload_max_file_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds the {settings.bulk_upload_max_file_bytes} byte limit.",
        )

    try:
        rows = parse_bulk_upload_file(file.filename, raw_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        payload = BulkFeedbackCreate(items=rows)
    except ValidationError as exc:
        # Only string-safe fields - exc.errors() can carry a raw exception
        # object in "ctx" for custom validators, which isn't JSON-encodable.
        detail = [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in exc.errors()]
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc

    return [
        _shape_feedback(_process_feedback_submission(db, item, owner_user_id=None), current_user)
        for item in payload.items
    ]


@router.get("/feedback", response_model=None)
def list_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    main_category: Optional[MainCategory] = Query(None),
    sentiment: Optional[Sentiment] = Query(None),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    source: Optional[FeedbackSource] = Query(None),
    property_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Union[FeedbackStaffRead, FeedbackSubmitterRead]]:
    # A GUEST/HOST caller is always scoped to their own rows here, at the
    # crud layer - never trust a client-supplied filter for this.
    owner_user_id = None if current_user.role in STAFF_ROLES else current_user.id
    items = crud.list_feedback(
        db,
        skip=skip,
        limit=limit,
        main_category=main_category,
        sentiment=sentiment,
        search=search,
        source=source,
        property_id=property_id,
        owner_user_id=owner_user_id,
    )
    return [_shape_feedback(item, current_user) for item in items]


@router.get("/feedback/{feedback_id}", response_model=None)
def get_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[FeedbackStaffRead, FeedbackSubmitterRead]:
    feedback = crud.get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    assert_owns_or_staff(feedback.user_id, current_user)
    return _shape_feedback(feedback, current_user)


@router.patch("/feedback/{feedback_id}", response_model=FeedbackStaffRead)
def update_feedback(
    feedback_id: int,
    payload: FeedbackAdminUpdate,
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_db),
) -> FeedbackStaffRead:
    feedback = crud.get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    updates = payload.model_dump(exclude_unset=True)
    updates.pop("tags", None)
    return crud.update_feedback_admin_fields(db, feedback, tag_names=payload.tags, **updates)
