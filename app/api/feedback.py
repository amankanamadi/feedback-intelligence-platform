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
    FeedbackDecisionCreate,
    FeedbackHostRead,
    FeedbackStaffRead,
    FeedbackSubmitterRead,
)
from app.core.config import get_settings
from app.core.security import (
    MANAGE_ROLES,
    RequireManager,
    STAFF_ROLES,
    assert_owns_or_staff,
    get_current_user,
    require_role,
)
from app.database import crud
from app.database.models import (
    Booking,
    BookingStatus,
    Feedback,
    FeedbackSource,
    FeedbackStatus,
    MainCategory,
    Priority,
    ResponsibleTeam,
    Role,
    Sentiment,
    User,
)
from app.database.session import get_db
from app.services.acknowledgement import generate_acknowledgement
from app.services.notifications import build_patch_notification
from app.services.routing import reconcile_main_category, route_to_team
from app.services.sla import compute_sla_due_at
from app.vector_store.embeddings import get_embedding
from app.vector_store.retrieval import find_duplicate_complaint, retrieve_similar_feedback

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


def _shape_host_feedback(feedback: Feedback) -> FeedbackHostRead:
    """Shapes a host-queue item - a reduced AI-context view, distinct from
    both FeedbackSubmitterRead and FeedbackStaffRead (see FeedbackHostRead's
    docstring). Kept as its own function rather than folded into
    _shape_feedback, which several other routes rely on staying a strict
    binary STAFF/else branch.
    """
    shaped = FeedbackHostRead.model_validate(feedback)
    shaped.property_name = feedback.property.name if feedback.property else None
    shaped.property_city = feedback.property.city if feedback.property else None
    return shaped


def _validate_property_id(db: Session, property_id: Optional[int]) -> None:
    if property_id is not None and crud.get_property(db, property_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Property {property_id} not found")


def _assert_can_submit_for_booking(booking: Booking, *, is_review: bool, current_user: User) -> None:
    """A booking's guest may always submit against it (review or
    complaint); staff may always act on behalf of anyone. A host may file
    a complaint about their own property's booking (e.g. "this guest
    trashed my place") but may never submit a *review* for it - reviews
    are guest-only by definition, and letting a host rate their own
    listing would corrupt the guest-only average_rating guarantee.
    """
    if current_user.role in STAFF_ROLES:
        return
    if current_user.id == booking.guest_id:
        return
    if not is_review and current_user.id == booking.property.host_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _validate_booking(
    db: Session, booking_id: Optional[int], *, is_review: bool, current_user: User
) -> Optional[Booking]:
    """Resolves and authorizes a stay-review/complaint's booking. A stay
    review additionally requires the booking to be COMPLETED (the guest
    workflow is "once a booking is completed...") and that no review has
    already been submitted for it - one review per stay.
    """
    if booking_id is None:
        return None

    booking = crud.get_booking(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking {booking_id} not found")
    _assert_can_submit_for_booking(booking, is_review=is_review, current_user=current_user)

    if is_review:
        if booking.status != BookingStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stay reviews can only be submitted for completed bookings.",
            )
        if crud.has_review_for_booking(db, booking_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A stay review has already been submitted for this booking.",
            )
    return booking


def _process_feedback_submission(
    db: Session, payload: FeedbackCreate, *, owner_user_id: Optional[int], current_user: User
) -> Feedback:
    """Create + embed + retrieve RAG context + classify + acknowledge a
    single item. Shared by the single-item and bulk endpoints so both go
    through identical logic. Each AI step degrades independently on
    failure (a failed embedding/classification never blocks storing the
    raw feedback); the acknowledgement step never fails since it's a pure
    template lookup, not a network call.
    """
    is_review = payload.overall_rating is not None
    booking = _validate_booking(db, payload.booking_id, is_review=is_review, current_user=current_user)
    # A review's property always matches its booking, regardless of
    # whatever property_id the client sent - the booking is authoritative.
    property_id = booking.property_id if booking is not None else payload.property_id
    _validate_property_id(db, property_id)

    feedback = crud.create_feedback(
        db,
        raw_text=payload.raw_text,
        owner_user_id=owner_user_id,
        submitter_user_id_legacy=payload.submitter_user_id_legacy,
        name=payload.name,
        email=payload.email,
        source=payload.source,
        property_id=property_id,
        version=payload.version,
        device=payload.device,
        browser=payload.browser,
        platform=payload.platform,
        booking_id=payload.booking_id,
        overall_rating=payload.overall_rating,
        cleanliness_rating=payload.cleanliness_rating,
        communication_rating=payload.communication_rating,
        checkin_rating=payload.checkin_rating,
        location_rating=payload.location_rating,
        value_rating=payload.value_rating,
    )

    embedding = None
    similar_examples: list[dict] = []
    duplicate_of_feedback_id: Optional[int] = None
    try:
        embedding = get_embedding(payload.raw_text)
        similar_examples = retrieve_similar_feedback(db, embedding, n_results=3, exclude_id=feedback.id)
        # Only complaint-style submissions can be "duplicates" of an
        # earlier one, and only within the same listing.
        if not is_review and property_id is not None:
            duplicate_match = find_duplicate_complaint(
                db, embedding, property_id=property_id, exclude_id=feedback.id
            )
            if duplicate_match is not None:
                duplicate_of_feedback_id = duplicate_match["id"]
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
            # A stay review's main_category is deterministic from the
            # workflow itself (ratings + a completed booking mean it's a
            # Guest Review, full stop) - never left to the AI's judgment,
            # even if a scathing review reads more like a complaint to it.
            # For everything else, the model's own main_category can
            # contradict its own sub_category (e.g. Guest Review paired
            # with Maintenance) - reconcile_main_category corrects that
            # using the sub_category's fixed taxonomy group, since letting
            # it stand would silently skip routing below for a genuinely
            # actionable complaint. Sentiment, themes, summary, priority,
            # and recommended_action still come from real AI analysis of
            # the written text.
            main_category = (
                MainCategory.GUEST_REVIEW
                if is_review
                else reconcile_main_category(classification.main_category, classification.sub_category)
            )
            # Routing/SLA only apply to actionable complaints/tickets, not
            # reviews - gated on the final main_category (not is_review),
            # since a no-rating submission can still be AI-classified as
            # a Guest Review on its own.
            responsible_team = None
            sla_due_at = None
            if main_category != MainCategory.GUEST_REVIEW:
                responsible_team = route_to_team(classification.sub_category)
                sla_due_at = compute_sla_due_at(classification.priority)
            feedback = crud.apply_classification(
                db,
                feedback,
                main_category=main_category,
                sub_category=classification.sub_category,
                sentiment=classification.sentiment,
                priority=classification.priority,
                confidence=classification.confidence,
                summary=classification.summary,
                theme_names=classification.themes,
                recommended_action=classification.recommended_action,
                root_cause=classification.root_cause,
                business_impact=classification.business_impact,
                executive_summary=classification.executive_summary,
                preventive_recommendation=classification.preventive_recommendation,
                responsible_team=responsible_team,
                sla_due_at=sla_due_at,
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

    if duplicate_of_feedback_id is not None:
        try:
            feedback = crud.set_duplicate_of(db, feedback, duplicate_of_feedback_id)
        except Exception:
            logger.exception("Duplicate-link storage failed for feedback %s", feedback.id)

    return feedback


@router.post("/feedback", response_model=None, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[FeedbackStaffRead, FeedbackSubmitterRead]:
    feedback = _process_feedback_submission(db, payload, owner_user_id=current_user.id, current_user=current_user)
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
        _shape_feedback(
            _process_feedback_submission(db, item, owner_user_id=None, current_user=current_user), current_user
        )
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
        _shape_feedback(
            _process_feedback_submission(db, item, owner_user_id=None, current_user=current_user), current_user
        )
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
    priority: Optional[Priority] = Query(None),
    status_: Optional[FeedbackStatus] = Query(None, alias="status"),
    responsible_team: Optional[ResponsibleTeam] = Query(None),
    escalated: Optional[bool] = Query(None),
    sla_breached: Optional[bool] = Query(None),
    unresolved: Optional[bool] = Query(None),
    has_duplicates: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Union[FeedbackStaffRead, FeedbackSubmitterRead]]:
    # A GUEST/HOST caller is always scoped to their own rows here, at the
    # crud layer - never trust a client-supplied filter for this.
    owner_user_id = None if current_user.role in STAFF_ROLES else current_user.id
    if current_user.role in STAFF_ROLES:
        # Only staff-facing (unscoped) reads pay for this bulk write - a
        # GUEST/HOST's own scoped view doesn't even expose sla_breached.
        crud.flag_overdue_sla_breaches(db)
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
        priority=priority,
        status=status_,
        responsible_team=responsible_team,
        escalated=escalated,
        sla_breached=sla_breached,
        unresolved=unresolved,
        has_duplicates=has_duplicates,
    )
    return [_shape_feedback(item, current_user) for item in items]


@router.get("/feedback/host-queue", response_model=None)
def list_host_complaint_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_: Optional[FeedbackStatus] = Query(None, alias="status"),
    unresolved: Optional[bool] = Query(None),
    current_user: User = Depends(require_role(Role.HOST)),
    db: Session = Depends(get_db),
) -> list[FeedbackHostRead]:
    # Must stay defined before GET /feedback/{feedback_id} below - that
    # route's path parameter has no type constraint in the path string
    # itself, so Starlette would otherwise match "host-queue" as a
    # feedback_id and 422 before this route is ever tried.
    crud.flag_overdue_sla_breaches(db)
    items = crud.list_feedback_for_host(
        db, current_user.id, skip=skip, limit=limit, status=status_, unresolved=unresolved
    )
    return [_shape_host_feedback(item) for item in items]


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


_HOST_ALLOWED_PATCH_FIELDS = {"status", "admin_response"}


def _assert_can_patch_feedback(feedback: Feedback, *, updates: dict, current_user: User) -> None:
    """Three tiers of PATCH access: MANAGE_ROLES get full access (unchanged
    from before this phase); TRUST_SAFETY gets full access but only for
    items actually routed to them (they resolve their own bypass-queue
    items, not general power over everything); a property's host gets a
    restricted subset (status/admin_response only) for their own routed
    items, and never for Trust & Safety items - that's the bypass, from
    the host's side.
    """
    if current_user.role in MANAGE_ROLES:
        return
    if current_user.role == Role.TRUST_SAFETY:
        if feedback.responsible_team == ResponsibleTeam.TRUST_AND_SAFETY:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if feedback.property is not None and current_user.id == feedback.property.host_id:
        if feedback.responsible_team == ResponsibleTeam.TRUST_AND_SAFETY:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        if not set(updates).issubset(_HOST_ALLOWED_PATCH_FIELDS):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.patch("/feedback/{feedback_id}", response_model=None)
def update_feedback(
    feedback_id: int,
    payload: FeedbackAdminUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[FeedbackStaffRead, FeedbackSubmitterRead]:
    feedback = crud.get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    updates = payload.model_dump(exclude_unset=True)
    _assert_can_patch_feedback(feedback, updates=updates, current_user=current_user)

    updates.pop("tags", None)
    updated = crud.update_feedback_admin_fields(db, feedback, tag_names=payload.tags, **updates)

    message = build_patch_notification(
        status_changed_to_resolved=updates.get("status") == FeedbackStatus.RESOLVED,
        admin_response_changed=updates.get("admin_response") is not None,
    )
    if message is not None and updated.user_id is not None:
        crud.create_notification(
            db, user_id=updated.user_id, message=message, link=f"/app/feedback/{updated.id}"
        )

    return _shape_feedback(updated, current_user)


@router.post("/feedback/{feedback_id}/decision", response_model=None)
def submit_feedback_decision(
    feedback_id: int,
    payload: FeedbackDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Union[FeedbackStaffRead, FeedbackSubmitterRead]:
    feedback = crud.get_feedback(db, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    if feedback.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if feedback.admin_response is None or feedback.guest_decision is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No pending resolution to decide on.",
        )

    updated = crud.apply_guest_decision(db, feedback, payload.decision)
    return _shape_feedback(updated, current_user)
